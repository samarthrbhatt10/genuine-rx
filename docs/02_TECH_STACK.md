# Tech Stack — Pinned Versions

Check this file before installing anything. Do not upgrade a pin without a reason written in
the commit message. Do not add a dependency that isn't listed here — flag it to the user
instead of silently pulling something new in.

## Automation Layer

| Package | Version | Why |
|---|---|---|
| `robotframework` | `7.1.x` | Core test/automation runner |
| `rpaframework` | `28.x` | PDF parsing (Jan Aushadhi), HTTP, scheduling helpers |
| `robotframework-browser` | `18.x` | Playwright-backed — handles JS-heavy pharmacy pages, harder to fingerprint than Selenium |
| `playwright` | `1.4x.x` | Installed as a dependency of `robotframework-browser`; run `rfbrowser init` once after install |

## Backend

| Package | Version | Why |
|---|---|---|
| `python` | `3.11.x` | Stable, matches RPA Framework's support matrix |
| `fastapi` | `0.11x.x` | Thin, async, typed — no heavier framework needed for this scope |
| `uvicorn[standard]` | `0.3x.x` | ASGI server |
| `sqlalchemy` | `2.0.x` | ORM for PostgreSQL, used only in the API layer, not inside RF suites |
| `psycopg[binary]` | `3.x` | Postgres driver |
| `alembic` | `1.1x.x` | Migrations — every schema change goes through a migration, never a manual `ALTER TABLE` |
| `redis` | `5.x` | Cache client |
| `rapidfuzz` | `3.x` | Fuzzy matching for OCR output → brand name resolution (C-optimized, much faster than `fuzzywuzzy`) |
| `pytesseract` | `0.3.x` | Tesseract OCR binding |
| `opencv-python-headless` | `4.x` | Image pre-processing (deskew, contrast) before OCR |
| `twilio` | `9.x` | WhatsApp Business API delivery |
| `apscheduler` | `3.1x.x` | Triggers the daily RPA run from within a long-running worker process |

## Frontend

| Package | Version | Why |
|---|---|---|
| `next` | `14.x` | SSR for the savings-calculator page; avoids SPA overhead for a mostly-single-visit flow |
| `react` | `18.x` | — |
| `typescript` | `5.x` | — |
| `tailwindcss` | `3.x` | — |

## Deployment

| Component | Target |
|---|---|
| Frontend | Vercel |
| FastAPI + RPA worker | Railway or Render (persistent VM — Playwright needs a real, stateful environment, not a serverless cold-start function) |
| PostgreSQL | Managed instance on the same platform as the API, to avoid cross-region latency on every request |
| Redis | Managed instance, same region as above |

## Explicitly Rejected (do not reintroduce without asking)

- `SeleniumLibrary` — rejected in favor of `robotframework-browser`; Playwright handles modern
  bot-detection better.
- `Scrapy` / raw `requests` scraping — rejected; loses Robot Framework's keyword-driven,
  testable structure that this course requires.
- Any cloud OCR API (Google Vision, AWS Textract) as the *default* path — Tesseract is free and
  offline. A cloud OCR fallback may be added later per `08_TOKEN_EFFICIENCY_RULES.md`, but only
  as a fallback, never the primary path.
- MongoDB — considered and reverted. This data is relational (medicines ↔ salts ↔ prices
  reference each other constantly) and Postgres's foreign keys catch data-entry mistakes a
  document store would silently accept.
