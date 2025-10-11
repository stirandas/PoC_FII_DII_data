# app/services/br_nse.py
"""Robust Playwright scraper for the combined (NSE, BSE, MSEI) FII/DII table with strict header scoping, env-overridable waits, reliable row readiness, and HTTP/2 fallbacks."""
from __future__ import annotations
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Page
import os
import re
import time

# -------------------------------
# Env-driven timeout/delay config
# -------------------------------

def _env_ms(name: str, default_ms: int) -> int:
    try:
        v = os.getenv(name)
        return int(v) if v is not None else default_ms
    except Exception:
        return default_ms

def _env_s(name: str, default_s: float) -> float:
    try:
        v = os.getenv(name)
        return float(v) if v is not None else default_s
    except Exception:
        return default_s

# Timeout and delay constants with env overrides (defaults tuned for NSE)
NAV_NETWORK_IDLE_MS        = _env_ms("NAV_NETWORK_IDLE_MS", 8000)      # page.wait_for_load_state("networkidle") [ms] [web:118]
HEADER_APPEAR_MS           = _env_ms("HEADER_APPEAR_MS", 12000)        # heading wait [ms] [web:36]
TABLE_VISIBLE_MS           = _env_ms("TABLE_VISIBLE_MS", 10000)        # table visible wait [ms] [web:36]
THEAD_READY_MS             = _env_ms("THEAD_READY_MS", 12000)          # thead ready wait [ms] [web:36]
ROW_WAIT_BUDGET_MS         = _env_ms("ROW_WAIT_BUDGET_MS", 15000)      # total row wait budget [ms] [web:36]
PAGE_NAV_DEFAULT_MS        = _env_ms("PAGE_NAV_DEFAULT_MS", 25000)     # page default nav timeout [ms] [web:5]
PAGE_ACTION_DEFAULT_MS     = _env_ms("PAGE_ACTION_DEFAULT_MS", 25000)  # page default action timeout [ms] [web:24]

# Small delays used during nudges/backoffs [seconds]
WHEEL_SCROLL_DELAY_S       = _env_s("WHEEL_SCROLL_DELAY_S", 0.25)      # scroll polling step [s] [web:36]
KEY_END_DELAY_S            = _env_s("KEY_END_DELAY_S", 0.5)            # after End key [s] [web:36]
KEY_HOME_DELAY_S           = _env_s("KEY_HOME_DELAY_S", 0.3)           # after Home key [s] [web:36]
ENGINE_RETRY_DELAY_S       = _env_s("ENGINE_RETRY_DELAY_S", 1.0)       # between browser engines [s] [web:118]

# -------------------------------
# Scraper configuration/constants
# -------------------------------

NSE_URL = "https://www.nseindia.com/reports/fii-dii"  # Target reports page hosting both tables. [web:6]
HEADER_TEXT = "FII/FPI & DII trading activity on NSE, BSE and MSEI in Capital Market Segment"  # Only target the long combined heading. [web:6]

JS_PARSE_TABLE = (
    "(el) => {\n"
    "  const thead = el.querySelector('thead');\n"
    "  const tbody = el.querySelector('tbody');\n"
    "  if (!thead || !tbody) return [];\n"
    "  const headers = Array.from(thead.querySelectorAll('th')).map(x => x.textContent.trim());\n"
    "  const out = [];\n"
    "  for (const tr of tbody.querySelectorAll('tr')) {\n"
    "    const cells = Array.from(tr.querySelectorAll('td')).map(x => x.textContent.trim());\n"
    "    if (cells.length === headers.length) {\n"
    "      const row = {};\n"
    "      headers.forEach((h, i) => row[h] = cells[i]);\n"
    "      out.push(row);\n"
    "    }\n"
    "  }\n"
    "  return out;\n"
    "}"
)  # In-page JS to map thead headers to tbody row cells as list[dict]. [web:24]

# -------------------------------
# Locators and synchronization
# -------------------------------

def _locate_table(page: Page):
    """
    Return a Locator for the combined (NSE, BSE, MSEI) table under the exact long heading,
    avoiding substring collisions with the first table. [web:36]
    """
    # Strict ARIA role-based heading exact match.
    header = page.get_by_role("heading", name=HEADER_TEXT, exact=True)  # Exact accessible-name match. [web:36]
    try:
        header.wait_for(timeout=HEADER_APPEAR_MS)  # Wait for the long heading to appear. [web:36]
        # Scope to nearest section/div containing the heading.
        region = header.locator("xpath=ancestor::*[self::section or self::div][1]")  # Nearest container. [web:36]
        # Pick the first table that follows this heading within that region.
        table = region.locator("xpath=.//following::*[self::table][1]").first  # Following table selection. [web:36]
        table.wait_for(state="visible", timeout=TABLE_VISIBLE_MS)  # Ensure it is visible. [web:24]
        return table  # Return the scoped table locator. [web:36]
    except Exception:
        pass  # Fall through to regex fallback. [web:36]

    # Regex fallback anchored to the full string to prevent substring matches.
    pattern = re.compile(rf"^{re.escape(HEADER_TEXT)}$")  # Full-string anchored regex. [web:36]
    h2 = page.get_by_text(pattern).first  # Text locator using regex pattern. [web:36]
    h2.wait_for(timeout=HEADER_APPEAR_MS)  # Wait for the heading by text. [web:36]
    region = h2.locator("xpath=ancestor::*[self::section or self::div][1]")  # Nearest container. [web:36]
    table = region.locator("xpath=.//following::*[self::table][1]").first  # Following table selection. [web:36]
    table.wait_for(state="visible", timeout=TABLE_VISIBLE_MS)  # Ensure it is visible. [web:24]
    return table  # Return the combined table locator. [web:36]

def _ensure_rows_rendered(page: Page, table_locator):
    """
    Wait up to ROW_WAIT_BUDGET_MS for at least one tbody row, nudging with gentle scrolling
    to trigger lazy rendering/virtualization if present. [web:36]
    """
    thead_th = table_locator.locator("thead th")  # Header cells locator. [web:24]
    tbody_tr = table_locator.locator("tbody tr")  # Row locator. [web:24]

    # Ensure thead exists so the structure is present.
    thead_th.first.wait_for(timeout=THEAD_READY_MS)  # Wait for at least one header cell. [web:24]

    # Scroll the table into view in case offscreen rows are virtualized.
    try:
        table_locator.scroll_into_view_if_needed(timeout=2000)  # Bring into viewport if needed. [web:28]
    except Exception:
        pass  # Non-fatal; continue. [web:36]

    # Condition-based wait with a bounded budget; poll row count and gently scroll.
    deadline = time.time() + (ROW_WAIT_BUDGET_MS / 1000.0)  # Compute deadline from ms budget. [web:36]
    while time.time() < deadline:
        try:
            if tbody_tr.count() > 0:  # Rows present. [web:24]
                return  # Success: rows have rendered. [web:24]
        except Exception:
            pass  # Ignore transient DOM issues and continue. [web:36]
        try:
            page.mouse.wheel(0, 200)  # Nudge scroll to trigger lazy render. [web:108]
        except Exception:
            pass  # Ignore if mouse wheel unsupported. [web:36]
        time.sleep(WHEEL_SCROLL_DELAY_S)  # Small backoff between polls. [web:36]

    # Final check before failing.
    try:
        if tbody_tr.count() > 0:  # One last check. [web:24]
            return  # Success on final check. [web:24]
    except Exception:
        pass  # Ignore and raise below. [web:36]
    raise RuntimeError("Combined table visible but has no rows after row-wait")  # Explicit error if empty. [web:36]

def _parse_table(page: Page, table_locator):
    handle = table_locator.element_handle()  # Get element handle to evaluate JS_PARSE_TABLE. [web:24]
    if not handle:
        raise RuntimeError("Table handle not available")  # Structural failure if no handle. [web:24]

    data = page.evaluate(JS_PARSE_TABLE, handle)  # First parse attempt. [web:24]
    if not data:
        # Light nudge for late cell renderers.
        try:
            page.keyboard.press("End"); time.sleep(KEY_END_DELAY_S)  # Scroll to bottom briefly. [web:36]
            page.keyboard.press("Home"); time.sleep(KEY_HOME_DELAY_S)  # Return to top. [web:36]
        except Exception:
            pass  # Ignore if keys not supported. [web:36]
        data = page.evaluate(JS_PARSE_TABLE, handle)  # Second parse attempt. [web:24]

    if not data:
        raise RuntimeError("Combined table located but empty after retries")  # No data despite readiness. [web:36]

    return data  # Return list[dict] data. [web:24]

# -------------------------------
# Main scraping flow
# -------------------------------

def _maybe_set_consent_cookies(context):
    """
    Optional: set consent cookies if site hides content until consent; adjust as needed. [web:118]
    """
    try:
        context.add_cookies([
            {
                "name": "consent", "value": "accepted",
                "domain": ".nseindia.com", "path": "/", "httpOnly": False, "secure": True, "sameSite": "Lax"
            },
        ])  # Example only; replace with actual cookie keys if required. [web:118]
    except Exception:
        pass  # Safe no-op if adding cookies fails. [web:118]

def _scrape_with_page(page: Page):
    # Navigate; prefer DOMContentLoaded then a short network idle for initial quietness.
    page.goto(NSE_URL, wait_until="domcontentloaded")  # DOM readiness gate. [web:5]
    try:
        page.wait_for_load_state("networkidle", timeout=NAV_NETWORK_IDLE_MS)  # Short network idle, not blocking. [web:5]
    except PWTimeout:
        pass  # Continue; table-scoped waits follow. [web:5]

    # Locate only the combined table under the long heading.
    table = _locate_table(page)  # Strict scoping to the second table. [web:36]

    # Ensure rows actually render before parsing.
    _ensure_rows_rendered(page, table)  # Condition-based readiness. [web:36]

    # Parse rows to list of dicts.
    return _parse_table(page, table)  # Return structured data. [web:24]

def fetch_json_data():
    """Scrape and return the combined NSE/BSE/MSEI FII/DII table as a list of dict rows. [web:6]"""
    with sync_playwright() as p:
        attempts = (
            (p.chromium, {"headless": True, "args": ["--headless=new", "--disable-http2", "--disable-quic"]}),  # Chromium with protocol flags. [web:5]
            (p.firefox, {"headless": True}),  # Firefox fallback. [web:5]
        )  # Try multiple engines to improve resilience. [web:5]
        last_err: Exception | None = None  # Track last error for surfacing. [web:5]
        for engine, launch_kwargs in attempts:
            browser = engine.launch(**launch_kwargs)  # Launch browser. [web:5]
            try:
                context = browser.new_context(
                    locale="en-US",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                )  # Realistic locale and UA. [web:5]
                _maybe_set_consent_cookies(context)  # Optional consent to avoid blocked content. [web:118]

                page = context.new_page()  # New page in context. [web:5]
                page.set_default_navigation_timeout(PAGE_NAV_DEFAULT_MS)  # Default nav timeout. [web:5]
                page.set_default_timeout(PAGE_ACTION_DEFAULT_MS)  # Default action timeout. [web:24]

                return _scrape_with_page(page)  # Execute scrape flow and return data. [web:5]
            except Exception as e:
                last_err = e  # Save error to raise if all engines fail. [web:5]
                time.sleep(ENGINE_RETRY_DELAY_S)  # Stagger between engines. [web:118]
            finally:
                try:
                    browser.close()  # Ensure browser is closed. [web:5]
                except Exception:
                    pass  # Ignore close failures. [web:5]
        if last_err:
            raise last_err  # Propagate the last encountered error. [web:5]
        raise RuntimeError("Unknown error while scraping combined NSE table")  # Safety net. [web:5]

if __name__ == "__main__":
    print(fetch_json_data())  # Run scraper and print list[dict] rows. [web:5]
