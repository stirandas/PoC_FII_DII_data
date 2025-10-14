# arc42 Architecture Documentation — PoC_FII_DII_data

Repository: stirandas/PoC_FII_DII_data  
Author: Generated for repository analysis (2025-10-14)  
Purpose: Scrape daily FII/DII equity flow data from NSE, persist to a database, notify via Telegram.

This document follows the arc42 template and is tailored to the code and artifacts present in the repository.

---

1. Requirements and Goals
- 1.1 Business goals
  - Provide an automated mechanism to obtain daily FII/DII equity flow data from the NSE portal.
  - Persist daily rows to a database for historical analysis.
  - Notify subscribers via Telegram when fresh data is observed.
  - Serve as a small, deployable PoC that can be scheduled or run manually.

- 1.2 Quality goals (non-functional)
  - Resilience of scraping: tolerate JS-rendered pages and UI timing issues.
  - Simplicity of deployment: single Docker image runs the job.
  - Observability: basic logs and deterministic success/failure for runs.
  - Maintainability: modular Python services; clear responsibilities per module.
  - Security: use environment variables for secrets (BOT_TOKEN, CHAT_ID, DATABASE_URL).

- 1.3 Constraints and context assumptions
  - Input data originates from NSE pages that may be dynamically rendered.
  - Network availability is required.
  - Environment variables supply DB URL and Telegram credentials.
  - The project is a PoC and not yet hardened for multi-tenant production.

---

2. Constraints (technical & organizational)
- Single Docker container as primary deployment artifact.
- Playwright is used for scraping (browsers installed in Docker image).
- SQLAlchemy is used for DB access; no migration tool present (e.g., Alembic missing).
- Minimal tests: small scripts in app/tests/ (not full pytest suite).
- .env and local environment usage for secrets; no secrets manager integrated.

---

3. System Scope and Context (big picture)
- Primary external systems:
  - NSE website (source of FII/DII tables).
  - Relational Database (POSTGRES, MySQL, etc. via DATABASE_URL).
  - Telegram Bot API (notification sink).

- Primary internal responsibilities:
  - Scrape the combined NSE/BSE/MSEI FII/DII table reliably.
  - Normalize and persist rows (date, category, buy, sell, net).
  - Send a Telegram message on new insertions; otherwise update timestamp.
  - Optionally, expose REST API endpoints (FastAPI routers present in code).

ASCII overview:
```
[Operator / Scheduler]
         |
         v
+---------------------------+
| Docker container          |
| - app_driver.py           |
| - br_nse.py (scraper)     |
| - ins_data.py / upd_data.py (processing) |
| - bot_json_msg.py (notifier) |
| - db.py (SQLAlchemy)      |
+---------------------------+
   |           |
   v           v
[NSE website] [Database]
                  |
                  v
              [Telegram Bot API]
```

---

4. Solution Strategy
- Use Playwright to render pages and extract tables reliably; try Chromium first, then Firefox fallback.
- Use in-page JavaScript to map thead headers to tbody row cells (ensures header/row alignment).
- Normalize raw scraped strings to typed values (dates, Decimal) before persisting.
- Use SQLAlchemy Session factory for DB operations; contextmanager for transaction scope.
- Use Telegram Bot API (sendMessage) for notifications; config via BOT_TOKEN and CHAT_ID.
- Deploy as a container running init.sh that executes Python driver module.

---

5. Building Block View (static decomposition — implementation-related)
Key modules and responsibilities:

- app/app_driver.py
  - Orchestrates: fetch_json_data → transform_rows → insert_eq_data → bot_json_msg or touch_timestamp.

- app/services/br_nse.py
  - Scraping logic using Playwright.
  - Table locating strategy:
    - Locate heading by exact long string (avoids collisions).
    - Scope to nearby region and take the first following table.
    - Fallback to regex matching on text locator.
  - Render/wait strategies and retries; JS table parsing and nudge logic.

- app/services/ins_data.py
  - Transform raw row dicts into DB-compatible values.
  - Insert logic to persist new rows; returns indication if fresh rows were inserted.

- app/services/upd_data.py
  - Update run timestamp (u_ts) for existing rows.
  - Uses session_scope to ensure commit/rollback behavior.

- app/services/bot_json_msg.py
  - Format rows to a Telegram-friendly <pre> HTML message and call Telegram API.
  - Validates BOT_TOKEN and CHAT_ID are set; raises TelegramSendError on issues.

- app/db.py
  - Creates SQLAlchemy engine and SessionLocal using DATABASE_URL environment variable.

- app/api/* (api_router.py)
  - FastAPI routers present (auth, users) — optional and not required by the PoC main flow.

- app/tests/*
  - Small run scripts that exercise scraping, update, and bot logic.

---

6. Runtime View (scenarios & runtime interactions)
Typical run sequence (single-run, non-scheduled):
1. Container starts; init.sh executes python -m app.app_driver (Dockerfile CMD).
2. app_driver.application_main_driver():
   - Calls fetch_json_data() in br_nse.py.
   - Playwright launches headless Chromium (args include --headless=new) and tries scraping:
     - New context and page, waits for DOM readiness and network idle best-effort.
     - Locates the long heading, scopes the nearest table, waits for rows to render.
     - Uses evaluated JS to parse table into list[dict].
   - Returns list of rows to app_driver.
3. app_driver calls transform_rows(payload) from ins_data.py.
4. insert_eq_data(payload) attempts to persist rows. If new rows inserted, returns True.
5. If fresh data:
   - bot_json_msg(json_data) formats and POSTs to Telegram API.
   - If bot_json_msg fails it raises TelegramSendError (handled by caller or bubbled).
   Else:
   - touch_timestamp(run_dt) updates u_ts for the existing run row.
6. app_driver exits with success/failure status.

Error handling highlights:
- Playwright attempts multiple engines and will raise the last error if all fail.
- DB session manager uses session_scope contextmanager to commit or rollback.
- Telegram send raises explicit TelegramSendError for missing configuration or send failures.

---

7. Deployment View (physical deployment)
- Build: Dockerfile builds image with Python 3.13, installs dependencies (requirements exported via Poetry), creates venv, installs Playwright and browsers, copies app, sets init.sh as entrypoint and runs app driver.
- Runtime environment variables required:
  - DATABASE_URL (mandatory)
  - BOT_TOKEN, CHAT_ID (for notifications)
  - Optional timeouts and wait overrides (TABLE_VISIBLE_MS, THEAD_READY_MS, etc.)
- Recommended runtime: run as scheduled job (Cron, Kubernetes CronJob, CI scheduled workflow) or invoked manually.
- Persistence: external relational DB reachable via DATABASE_URL; use a managed DB for production.

---

8. Cross-cutting Concepts
- Configuration management: dotenv for local dev; production should use a secrets manager (AWS Secrets Manager, Vault, SSM).
- Resilience: Playwright engine fallback and retry/backoff logic.
- Transactions: session_scope ensures consistency with commit/rollback.
- Observability: The code currently relies on stdout prints and Python exceptions; recommend structured logging.
- Security: Credentials never committed; use environment variables. Communications with Telegram use HTTPS.

---

9. Architecture Decisions (selected)
- AD1: Use Playwright (not requests + BeautifulSoup)
  - Rationale: NSE pages may be JS-rendered; Playwright provides reliable rendering and browser automation.
  - Consequence: Larger container image and need to install browsers & dependencies.

- AD2: Single Docker container to run the pipeline
  - Rationale: Simplicity for PoC and reproducibility.
  - Consequence: All concerns bundled together; for scale, split into microservices or scheduled jobs.

- AD3: Store DB connection as DATABASE_URL and use SQLAlchemy session factory
  - Rationale: Standardized DB access and portability to multiple RDBMS.
  - Consequence: Need to add migrations tooling (Alembic) to manage schema evolution.

- AD4: Use Telegram for notifications
  - Rationale: Simple push-notify channel for PoC.
  - Consequence: Add retry/backoff for POSTs and option for other channels later.

- AD5: Use environment variables and .env for config in PoC
  - Rationale: Simple local configurability.
  - Consequence: Production must use secure secret storage.

---

10. Quality Scenarios (examples)
- Q1 (Robustness): If the NSE table takes longer to render (slow network / client-side renderer), the scraper should retry and nudge; configured timeouts should be sufficient. Test by throttling network and verifying fallback to keyboard nudges and JavaScript re-evaluation.
- Q2 (Resilience): If Chromium fails to launch, Firefox should be tried. Test by disabling Chromium in container.
- Q3 (Data correctness): The in-page JS parser must map headers to the correct cells. Test by comparing header count vs. cell count; rows with mismatched counts should be dropped and logged.
- Q4 (Idempotency): Running the job again for the same run_dt should not produce duplicate rows. insert_eq_data should detect existing keys (PK run_dt) and avoid duplicate inserts; touch_timestamp should update u_ts instead.
- Q5 (Notification): If BOT_TOKEN is missing or invalid, the system should raise TelegramSendError and not silently succeed.

---

11. Risks and Technical Debt
- No DB migrations (risk of schema drift): mitigation—introduce Alembic and baseline migration.
- Limited automated tests: convert scripts in app/tests into a pytest suite and add CI.
- Secrets handling via .env: move to secret manager before production.
- Logging/monitoring not integrated: add structured logging, metrics, and health endpoints.
- No scheduler in repo: container must be scheduled externally; consider adding a Kubernetes CronJob or GitHub Actions workflow.
- Function return inconsistencies (e.g., upd_data.touch_timestamp returns None rather than the number of rows updated): code cleanup recommended.

---

12. Appendix: How to run locally (developer guide)
- Pre-requisites:
  - Python 3.13 (or use Dockerfile), Playwright dependencies for local run, a running DB reachable via DATABASE_URL.
- Local run:
  1. Create .env with:
     - DATABASE_URL (e.g., postgres://user:pw@host:5432/dbname)
     - BOT_TOKEN and CHAT_ID (if you want notifications)
  2. Install dependencies (poetry or pip after export).
  3. Install Playwright browsers: playwright install --with-deps chromium firefox
  4. Run: python -m app.app_driver
- Docker:
  1. docker build -t fii-dii-poc .
  2. docker run --rm -e DATABASE_URL="..." -e BOT_TOKEN="..." -e CHAT_ID="..." fii-dii-poc

---

13. Recommendations / Next Steps
- Add Alembic migrations and an initial migration that creates the t_nse_fii_dii_eq_data table(s).
- Convert test scripts to pytest and add GitHub Actions that:
  - Lint, run unit tests (mock Playwright / use recorded fixtures).
  - Optionally run an integration smoke test against a test DB.
- Replace .env for production with a secrets manager.
- Add structured logging (python logging with JSON formatter) and a health endpoint in FastAPI for readiness/liveness.
- Add retry/exponential-backoff on Telegram API calls and add metrics for success/failure counts.
- Add an automated scheduler configuration (GitHub Actions scheduled workflow or Kubernetes CronJob) and an upgrade path for scaling scraper (e.g., worker queue).
- Fix small issues: ensure functions return meaningful values (e.g., touch_timestamp should return count of updated rows), remove any unreachable code, and add clear CLI arguments or environment-driven mode selection.

---

14. Glossary
- PoC: Proof of Concept
- FII: Foreign Institutional Investor
- DII: Domestic Institutional Investor
- NSE: National Stock Exchange (of India)
- Playwright: headless browser automation library
- DB: Relational Database (SQL)
- u_ts: update timestamp column

---

What I did and what's next
- I inspected the repository layout and code snippets and produced an arc42-structured architecture document that maps components, runtime flows, deployment aspects, quality scenarios, known risks, and recommended next steps.
- If you want, I can now:
  - Create this ARCHITECTURE_arc42.md file in the repository (open a PR).
  - Generate PlantUML diagrams for Context/Container/Component views and add them to the repo.
  - Draft ADR(s) for key decisions (Playwright choice, Docker deployment, migrations).
Which of these should I do next? I can create the file in a branch and open a pull request for you.