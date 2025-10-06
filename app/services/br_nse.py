
"""The Playwright scraper navigates to the NSE page, waits for a header text, evaluates a DOM-walking JS function to find the first table after that header, 
parses the thead/tbody into a list of dict rows, and returns that JSON; it retries once if the table isn’t ready yet. 
"""

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import json
import time

NSE_URL = "https://www.nseindia.com/reports/fii-dii"
HEADER_SNIPPET = "FII/FPI & DII trading activity on NSE in Capital Market Segment"

# Optional: set HTTPS proxy via env if needed for WAF/network stability

JS_FIND_PARSE = """
(headerText) => {
  // Find an element whose text contains the headerText (case-sensitive)
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null);
  const hits = [];
  while (walker.nextNode()) {
    const el = walker.currentNode;
    const t = el.textContent ? el.textContent.trim() : "";
    if (t.includes(headerText)) hits.push(el);
  }
  if (!hits.length) return "JSERROR:header-not-found";

  function firstTableAfter(node) {
    // Scan forward through DOM order to find first TABLE node
    const it = document.createNodeIterator(document.body, NodeFilter.SHOW_ELEMENT);
    let cur;
    // advance to node
    while ((cur = it.nextNode())) {
      if (cur === node) break;
    }
    while ((cur = it.nextNode())) {
      if (cur.tagName === "TABLE") return cur;
    }
    return null;
  }

  let table = null;
  for (const h of hits) {
    table = firstTableAfter(h);
    if (table) break;
  }
  if (!table) return "JSERROR:table-not-found";

  const thead = table.querySelector('thead');
  const tbody = table.querySelector('tbody');
  if (!thead || !tbody) return "JSERROR:thead-or-tbody-missing";

  const headers = Array.from(thead.querySelectorAll('th')).map(x => x.textContent.trim());
  const out = [];
  for (const tr of tbody.querySelectorAll('tr')) {
    const cells = Array.from(tr.querySelectorAll('td')).map(x => x.textContent.trim());
    if (cells.length === headers.length) {
      const row = {};
      headers.forEach((h, i) => row[h] = cells[i]);
      out.push(row);
    }
  }
  return out;
}
"""

def fetch_json_data():
    with sync_playwright() as p:
        # Try Firefox first to avoid Chromium HTTP/2 quirks
        browser = p.firefox.launch(headless=True)
        #print("after browser launch")
        try:
            #print("insider try")
            context = browser.new_context(locale="en-US")
            page = context.new_page()
            # Longer timeouts for slow loads
            page.set_default_navigation_timeout(10000)
            page.set_default_timeout(10000)

            # Navigate and wait for any distinctive text on the page body instead of table visibility
            page.goto(NSE_URL, wait_until="domcontentloaded")
            # Wait for the header text or a key phrase from the page
            try:
                page.wait_for_selector(f"text={HEADER_SNIPPET}", timeout=8000)
                #print("Header text found")
            except PWTimeout:
                # Fallback: wait for a more generic keyword likely present on the page
                page.wait_for_selector("text=FII/FPI", timeout=8000)
                #print("Fallback header text found")

            # Small settle time
            time.sleep(1)

            data = page.evaluate(JS_FIND_PARSE, HEADER_SNIPPET)
            #print("After first JS evaluation")
            #print(data)
            if isinstance(data, str) and data.startswith("JSERROR:"):
                # Retry once after a longer wait to allow late rendering
                time.sleep(2.5)
                data = page.evaluate(JS_FIND_PARSE, HEADER_SNIPPET)
                #print("inside if isinstance ", data)

            if isinstance(data, str) and data.startswith("JSERROR:"):
                raise RuntimeError(f"Page parse error: {data}")
            if not data:
                raise RuntimeError("Target table empty or not found")
            return(data)
        finally:
            try:
                browser.close()
            except Exception:
                pass

if __name__ == "__main__":
    fetch_json_data()
