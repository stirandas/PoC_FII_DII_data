"""
fetch_json_data.py

Purpose:
- Provide a small, reusable client to fetch JSON from NSE's public endpoint:
    https://www.nseindia.com/api/fiidiiTradeNse
- NSE often rejects "non-browser" requests; the client first visits a normal
  webpage to establish cookies, then calls the JSON API with the same session. [web:336][web:335]

Design:
- NseClient: holds a single requests.Session to reuse connections, headers,
  and cookies across multiple calls. This is better for performance and reliability
  vs. creating a new session for each call. [web:336][web:335]
- get_fiidii_trade_json(): convenience one-shot function that creates a client,
  warms it up, and returns the JSON. Useful in scripts or simple routes. [web:347]

Usage:
- Import into FastAPI routes or background tasks:
    from app.services.fetch_json_data import NseClient, get_fiidii_trade_json [web:347]
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import requests  # HTTP client used for session, cookies, headers, and retries. [web:336]

# Browser-like headers:
# - User-Agent: Pretend to be a modern desktop browser, which NSE's CDN expects. [web:335]
# - Accept/Encoding: Express common browser preferences (JSON, gzip/br), improving compatibility. [web:335]
# - Referer/Origin: Some NSE endpoints check these for basic origin heuristics. [web:329]
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nseindia.com/",
    "Origin": "https://www.nseindia.com",
}


class NseClient:
    """
    Reusable client that:
    1) boots the session by visiting an HTML page to set cookies, and
    2) uses the same session to call the JSON API reliably. [web:336][web:335]
    """

    BASE = "https://www.nseindia.com"  # Root domain for building URLs. [web:336]
    HOME_PATHS = ["/", "/market-data"]  # Candidate pages that typically set cookies quickly. [web:336]
    FII_DII_PATH = "/api/fiidiiTradeNse"  # Target JSON endpoint for FII/DII data. [web:343]

    def __init__(self, timeout: int = 20):
        # A session persists headers and cookies across requests, which is essential for NSE. [web:336]
        self.sess = requests.Session()  # Reuse the TCP connection and cookie jar. [web:336]
        self.sess.headers.update(BROWSER_HEADERS)  # Make every request look like a browser. [web:335]
        self.timeout = timeout  # Per-request timeout for responsiveness under network issues. [web:336]

    def boot_session(self) -> None:
        """
        Warm up the session by visiting an HTML page to receive cookies.
        Many 401/403 failures disappear after this warm-up. [web:336][web:335]
        """
        last_exc: Optional[Exception] = None  # Track the last error to report if all attempts fail. [web:336]
        for i, path in enumerate(self.HOME_PATHS):
            try:
                r = self.sess.get(f"{self.BASE}{path}", timeout=self.timeout)  # Perform a GET to set cookies. [web:336]
                # A 200/301/302 usually indicates the edge/CDN processed the request and set cookies. [web:336]
                if r.status_code in (200, 301, 302):
                    return  # Cookies likely set; proceed. [web:336]
                last_exc = RuntimeError(f"Unexpected status {r.status_code} on warm-up path {path}")  # Save reason. [web:336]
            except Exception as e:
                last_exc = e  # Capture network or TLS exceptions for final reporting. [web:336]
            time.sleep(0.7 + 0.3 * i)  # Small backoff between paths to be polite and let cookies propagate. [web:336]
        if last_exc:
            # If none of the pages worked, surface the last error to the caller.
            raise last_exc  # Caller can decide to retry at a higher level. [web:336]

    def get_fiidii_trade(self) -> List[Dict[str, Any]]:
        """
        Fetch the FII/DII cash market activity JSON.
        Returns a list of objects with fields like category, date, buyValue, etc. [web:343]
        """
        url = f"{self.BASE}{self.FII_DII_PATH}"  # Build the absolute endpoint URL. [web:343]
        r = self.sess.get(url, timeout=self.timeout)  # First attempt using warmed session. [web:336]
        if r.ok:
            return r.json()  # Parse and return JSON on success. [web:343]

        # If the first try fails (e.g., a transient 403), wait briefly and try once more. [web:336]
        time.sleep(0.8)  # Short backoff; NSE may finalize cookies after first API attempt. [web:336]
        r = self.sess.get(url, timeout=self.timeout)  # Second attempt. [web:336]
        r.raise_for_status()  # If still failing, bubble up the HTTP error to the caller. [web:336]
        return r.json()  # Return JSON on success. [web:343]


def get_fiidii_trade_json() -> List[Dict[str, Any]]:
    """
    One-shot convenience function:
    - Create a client
    - Warm it up
    - Fetch and return the JSON payload
    This is handy for scripts or simple routes without managing client lifecycle. [web:347]
    """
    client = NseClient()  # Construct a client per call for simplicity in one-off usage. [web:347]
    client.boot_session()  # Establish cookies to reduce 401/403 risks. [web:336][web:335]
    return client.get_fiidii_trade()  # Return parsed JSON to the caller. [web:343]
