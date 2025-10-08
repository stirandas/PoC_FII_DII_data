# app/services/br_nse.py
"""Robust Playwright scraper for NSE FII/DII table with scoped waits and HTTP/2 fallbacks."""
from __future__ import annotations
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Page
import time


NSE_URL = "https://www.nseindia.com/reports/fii-dii"
HEADER_TEXT = "FII/FPI & DII trading activity on NSE in Capital Market Segment"


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
)


def _locate_table(page: Page):
    """Return a Locator for the target table, using robust scoping and fallback."""
    # Try role-based heading first (accessible name)
    header = page.get_by_role("heading", name=HEADER_TEXT, exact=True)
    try:
        header.wait_for(timeout=12000)
        region = header.locator("xpath=ancestor::*[self::section or self::div][position()<=3]").first
        table = region.locator("table").first
        table.wait_for(state="visible", timeout=10000)
        return table
    except Exception:
        # Fallback: text-based anchor
        try:
            h2 = page.get_by_text(HEADER_TEXT, exact=True).first
            h2.wait_for(timeout=8000)
            region = h2.locator("xpath=ancestor::*[self::section or self::div][position()<=3]").first
            table = region.locator("table").first
            table.wait_for(state="visible", timeout=8000)
            return table
        except Exception:
            # Final fallback: any visible table with proper thead/tbody and at least one row
            table = page.locator("table").filter(
                has=page.locator("thead th")
            ).filter(
                has=page.locator("tbody tr")
            ).first
            table.wait_for(state="visible", timeout=30000)
            return table


def _scrape_with_page(page: Page):
    # Navigate and settle
    page.goto(NSE_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass


    table = _locate_table(page)


    # Scoped waits to this specific table
    thead_th = table.locator("thead th")
    tbody_tr = table.locator("tbody tr")
    thead_th.first.wait_for(timeout=12000)
    try:
        tbody_tr.first.wait_for(timeout=12000)
    except Exception:
        time.sleep(1.5)
        tbody_tr.first.wait_for(timeout=8000)


    handle = table.element_handle()
    if not handle:
        raise RuntimeError("Table handle not available")


    data = page.evaluate(JS_PARSE_TABLE, handle)
    if not data:
        time.sleep(2.0)
        data = page.evaluate(JS_PARSE_TABLE, handle)


    if not data:
        try:
            page.keyboard.press("End"); time.sleep(1.5)
            page.keyboard.press("Home"); time.sleep(1.0)
        except Exception:
            pass
        data = page.evaluate(JS_PARSE_TABLE, handle)


    if not data:
        raise RuntimeError("Table located but empty after retries")


    return data


def fetch_json_data():
    """Scrape and return the NSE FII/DII table as a list of dict rows."""
    with sync_playwright() as p:
        attempts = (
            (p.chromium, {"headless": True, "args": ["--headless=new", "--disable-http2", "--disable-quic"]}),
            (p.firefox, {"headless": True}),
        )
        last_err: Exception | None = None
        for engine, launch_kwargs in attempts:
            browser = engine.launch(**launch_kwargs)
            try:
                context = browser.new_context(
                    locale="en-US",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                try:
                    context.clear_cookies()
                except Exception:
                    pass
                page = context.new_page()
                page.set_default_navigation_timeout(30000)
                page.set_default_timeout(30000)


                return _scrape_with_page(page)
            except Exception as e:
                last_err = e
                time.sleep(1.0)
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
        if last_err:
            raise last_err
        raise RuntimeError("Unknown error while scraping NSE table")


if __name__ == "__main__":
    print(fetch_json_data())
