```markdown
# C4 Model Architecture: PoC_FII_DII_data

Repository: stirandas/PoC_FII_DII_data  
Purpose: Scrape daily FII/DII equity flow data from the NSE portal, persist it and notify via Telegram.

This document presents the architecture in the C4 model (Context, Container, Component, Code/Deployment). It is written as a single-file reference for maintainers and reviewers.

## 1 — System Context (C1)

Goal
- Automate retrieval of daily FII/DII table(s) from the NSE website, transform and persist them, then notify interested parties (Telegram) if fresh data is found.

Primary external actors
- NSE website (data source): publicly-hosted pages that contain FII/DII tables.
- Telegram Bot API: receives formatted messages from the system.
- Relational Database (DB): stores processed rows for historical queries.
- Operator / Developer: deploys, configures and monitors the system.

High-level responsibilities
- Periodically (or manually) run the PoC to fetch the latest FII/DII table.
- Transform scraped HTML table into structured rows (Date, Category, Buy, Sell, Net).
- Insert or update database rows and mark timestamps.
- Send Telegram messages when new data is inserted.

Context diagram (ASCII)
```
  [Operator/CI]                     [Telegram]
        |                                ^
        v                                |
  +----------------------+         +-----+-------+
  | PoC_FII_DII_data App |-------->| Telegram API|
  | (Docker container)   |         +-------------+
  |  - Scraper (Playwright)
  |  - Processor
  |  - Notifier (Telegram)
  |  - Optional: FastAPI
  +----------+-----------+
             |
             v
      +------+-------+
      |   Database    |
      | (SQL, via DB) |
      +---------------+

  NSE Website ---> (scraped by Scraper component)
```

## 2 — Container Diagram (C2)

Main containers/processes (runtime)

- Docker container (single deployment unit)
  - Entrypoint: `init.sh` → runs the app driver
  - Built with Dockerfile: creates venv, installs dependencies, installs Playwright browsers

- App process (Python)
  - app/app_driver.py — orchestration entrypoint
  - app/services/br_nse.py — scraper using Playwright (chromium / firefox fallback)
  - app/services/ins_data.py — transform and insert data into DB (not fully shown in repo snippets)
  - app/services/upd_data.py — update timestamps for run dates
  - app/services/bot_json_msg.py — formats and sends Telegram messages
  - app/db.py — SQLAlchemy engine and session factory
  - app/api/* — FastAPI routers and endpoints (present, likely optional for PoC)
  - app/tests/* — simple test scripts used for local verification

- External persistent store
  - SQL database (configured by `DATABASE_URL` environment variable)

- External services
  - NSE website (HTTP(s) pages)
  - Telegram Bot API (HTTP REST for sendMessage)

Container interaction summary
- App process scrapes NSE → transforms rows → persists into DB via SQLAlchemy → sends Telegram via HTTP POST to Telegram API.
- Optional: App exposes API endpoints via FastAPI (present in codebase) for future integrations.

## 3 — Component Diagram (C3)

Breakdown of important components in the Python app:

- app_driver.py
  - Role: orchestrates one run: fetch, transform, insert, notify, or update timestamp.
  - Flow: fetch_json_data() → transform_rows() → insert_eq_data() → bot_json_msg() or touch_timestamp()

- br_nse.py
  - Role: robust scraping of combined NSE/BSE/MSEI FII/DII table using Playwright.
  - Important behaviors:
    - Attempts Chromium first then Firefox.
    - Scopes table by exact long heading to avoid collisions.
    - Waits for relevant elements and uses in-page JS to map <thead> headers to <tbody> cells.
    - Has retry/backoff patterns and optional consent cookie injection.
  - Timeouts and environment-overridable waits are defined (e.g., TABLE_VISIBLE_MS).

- ins_data.py (transform + insert)
  - Role: convert scraped rows into DB-friendly types (dates, decimals), and perform inserts.
  - Interacts with app/db.py's session factory.
  - Returns indication whether fresh data was found (drives notifications).

- upd_data.py
  - Role: update timestamp (u_ts) for a given run date, uses session_scope helper.

- bot_json_msg.py
  - Role: format rows into a text payload and call Telegram sendMessage endpoint.
  - Loads BOT_TOKEN and CHAT_ID from environment (.env) via python-dotenv.
  - Raises TelegramSendError when configuration or send fails.

- db.py
  - Role: central place to create SQLAlchemy engine and SessionLocal using DATABASE_URL env var.
  - Session factory used across services.

- api_router.py (FastAPI)
  - Role: contains routers for auth and users endpoints; shows intent to expose REST API.

- tests
  - Small scripts to exercise components (scraper, notifier, updater) for local verification.

Component diagram (short ASCII)
```
[app_driver] -> [br_nse scraper] -> [ins_data transformer] -> [db (SQLAlchemy)]
                                       |
                                       v
                                 [bot_json_msg notifier] -> [Telegram API]
```

## 4 — Code / Deployment (C4)

Files & code mapping (representative)
- Dockerfile — builds container using Python 3.13, installs Poetry to export requirements, installs Playwright and browsers, sets ENTRYPOINT to init.sh, final CMD runs the app module: `python -m app.app_driver`
- init.sh — entry script (not shown in file snippets, but used as entrypoint)
- pyproject.toml / poetry.lock — dependency management
- .env (local, not in repo) — BOT_TOKEN, CHAT_ID, DATABASE_URL, and optional timeout overrides

Runtime requirements
- Environment variables:
  - DATABASE_URL — required (app/db.py will raise if missing)
  - BOT_TOKEN, CHAT_ID — required to send Telegram messages (bot_json_msg raises if missing)
- Playwright browsers require additional packages inside the container; Dockerfile already uses `playwright install --with-deps chromium firefox`.

Deployment steps (high-level)
1. Build Docker image: docker build -t fii-dii-poc .
2. Run container with environment and DB connectivity:
   - docker run -e DATABASE_URL="..." -e BOT_TOKEN="..." -e CHAT_ID="..." --rm fii-dii-poc
3. App entrypoint executes driver which performs a single run.

Database
- The code uses SQLAlchemy core/session and raw SQL text for update queries (see upd_data.touch_timestamp).
- Migrations are not present in the repo; adding Alembic or a migration plan is recommended.

## 5 — Data Flow (sequence)

1. Entry (manual run or scheduled container run)
2. br_nse.fetch_json_data uses Playwright to open the NSE page and locate the combined table.
3. br_nse parses rows into list[dict] (keys derived from table headers).
4. ins_data.transform_rows converts field formats (dates, decimals) and normalizes.
5. ins_data.insert_eq_data writes rows to DB; returns boolean indicating if fresh data was inserted.
6. If fresh data:
   - bot_json_msg formats text and posts to Telegram API.
   Else:
   - upd_data.touch_timestamp updates u_ts for the existing row (housekeeping).
7. Exit.

## 6 — Design decisions & rationale

- Use Playwright: more resilient than raw requests + BeautifulSoup for JS-rendered tables; supports multiple engines for fallback.
- Single container PoC: keeps deployment simple for proof-of-concept.
- Environment-driven config: secrets and timeouts are environment variables to keep code generic.
- SQLAlchemy session factory: central DB access pattern, session_scope context manager used for safe commit/rollback.

## 7 — Known gaps, issues & risks

- No DB migration tooling (Alembic) — schema drift risk.
- No scheduler in repo (cron/airflow) — currently run via container/CI.
- Tests are lightweight scripts (not pytest test suite) — limited coverage.
- init.sh and some other operational scripts are not listed in this document — review for robustness.
- Environment secrets in .env — ensure secure secret management in production.
- Some functions (e.g., upd_data.touch_timestamp) return None instead of expected counts; review return values and error handling.

## 8 — Recommendations & next steps

Immediate (to harden PoC)
- Add Alembic and migrations for DB schema management.
- Convert test scripts to pytest with CI pipeline (GitHub Actions) that runs smoke tests.
- Add a health-check endpoint (FastAPI) and expose minimal metrics for uptime/latency.
- Improve error handling and logging (structured logs, log levels).
- Add a scheduler (cron/CI scheduled workflow, or Kubernetes CronJob) for automated daily runs.

Longer-term / enhancements
- Add feature toggle / config for multiple notification channels (Slack, email).
- Add retries and exponential backoff for Telegram POST on transient errors.
- Add a canonical DTO and validation (pydantic) for scraped rows; use it in API and storage layers.
- Add a PlantUML or Structurizr visual artifact for C1–C3 diagrams and check it into the repo.

## 9 — Quick developer notes

- Run the scraper locally:
  - create .env with DATABASE_URL (point to a test DB)
  - ensure Playwright browsers are installed (or run inside Docker image built by provided Dockerfile)
  - run: python -m app.app_driver
- Useful files:
  - Dockerfile — reproducible runtime
  - app/services/br_nse.py — scraping logic with careful element scoping
  - app/services/bot_json_msg.py — telegram integration, requires BOT_TOKEN and CHAT_ID
  - app/db.py — DB connection via DATABASE_URL

---

Document created to capture the architecture in the C4 model for this repository. If you want, I can:
- Add PlantUML files for C1–C3 diagrams and commit them to the repo.
- Draft a PR that adds this markdown file to the repository root and includes basic CI checks that run the lightweight tests.
- Produce an ADR addressing DB migrations and secret management.

Tell me which of those you'd like me to do next and I will prepare the changes.
```