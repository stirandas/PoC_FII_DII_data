# PoC_FII_DII_data

Short description
- Purpose: Scrape daily FII/DII equity flow data from the NSE portal, persist it to a database, and notify via Telegram.

Quick links
- Full architecture docs: docs/index.md
- ADRs: docs/adr/
- How to run: see docs/run.md (or the "How to run locally" section in docs/index.md)

Quick start (example)
1. Create a `.env` with DATABASE_URL, BOT_TOKEN and CHAT_ID.
2. Build image: `docker build -t fii-dii-poc .`
3. Run: `docker run --rm -e DATABASE_URL="..." -e BOT_TOKEN="..." -e CHAT_ID="..." fii-dii-poc`

Contributing
- See docs/CONTRIBUTING.md for development, testing, and CI notes.

License
- MIT. See LICENSE file for details.