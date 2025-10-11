# app/services/bot_json_msg.py
from __future__ import annotations
import os
import requests
from typing import Any, Dict, List
from dotenv import load_dotenv

# Load .env for BOT_TOKEN and CHAT_ID
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage" if BOT_TOKEN else None
class TelegramSendError(Exception):
    pass

def _format_rows_to_text(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "<pre>No data</pre>"
    run_date = rows[0].get("Date", "")
    lines = [f"FII/DII Equity Flows — {run_date}"]
    for r in rows:
        cat = str(r.get("Category", "")).strip()
        buy = str(r.get("Buy Value(₹ Crores)", "")).strip()
        sell = str(r.get("Sell Value (₹ Crores)", "")).strip()
        net = str(r.get("Net Value (₹ Crores)", "")).strip()
        lines.append(f"{cat}: Buy {buy} | Sell {sell} | Net {net}")
    return f"<pre>{chr(10).join(lines)}</pre>"

def bot_json_msg(payload: Dict[str, Any] | List[Dict[str, Any]]) -> None:
    """
    Send the given DII/FII JSON as a Telegram message.
    Accepts a single dict or a list of dicts with keys:
      Category, Date, Buy Value(₹ Crores), Sell Value (₹ Crores), Net Value (₹ Crores)
    Uses BOT_TOKEN and CHAT_ID from .env only.
    Returns None on success; raises TelegramSendError on failure.
    """
    if not BOT_TOKEN:
        raise TelegramSendError("BOT_TOKEN missing in environment (.env)")
    if not CHAT_ID:
        raise TelegramSendError("CHAT_ID missing in environment (.env)")
    if API_URL is None:
        raise TelegramSendError("Invalid API URL (BOT_TOKEN missing).")

    rows: List[Dict[str, Any]]
    if isinstance(payload, dict):
        rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise TelegramSendError("payload must be a dict or a list of dicts")

    text = _format_rows_to_text(rows)

    body = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    resp = requests.post(API_URL, json=body, timeout=10.0)
    if resp.status_code != 200:
        raise TelegramSendError(f"HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    if not data.get("ok", False):
        raise TelegramSendError(f"Telegram error: {data.get('description', 'Unknown error')}")
    return None
