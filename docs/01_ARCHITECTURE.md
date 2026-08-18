# Architecture

## Layer Diagram

```
+-------------------------------------------------------------+
|                     PRESENTATION LAYER                       |
|   Next.js 14 web app   |   WhatsApp/SMS delivery (Twilio)    |
+-------------------------------------------------------------+
                              |  REST (FastAPI)
+-------------------------------------------------------------+
|                    APPLICATION / API LAYER                   |
|  FastAPI: resolve-medicine | get-substitutes | savings-calc  |
+-------------------------------------------------------------+
              |                      |                    |
+----------------+   +-------------------+   +-------------------+
|  OCR SERVICE   |   |  MATCHING ENGINE   |   |  RPA / AUTOMATION |
|  Tesseract +   |   |  Salt normalizer + |   |  LAYER            |
|  fuzzy match   |   |  ranking logic     |   |  Robot Framework  |
+----------------+   +-------------------+   |  + RPA Framework  |
   (offline,             (pure Python,       |  (scheduled runs) |
    no network calls)     deterministic)     +-------------------+
+-------------------------------------------------------------+
|                       DATA LAYER                              |
|  PostgreSQL (medicines, salts, price_history, users)          |
|  Redis (hot-path cache: salt lookups, last-known prices)      |
+-------------------------------------------------------------+
```

## Hard Boundaries (do not blur these)

- **OCR Service** never touches the network. It runs Tesseract locally and returns raw text.
  It does not call an LLM to "clean up" the text — that's the Matching Engine's fuzzy-match
  job, done with `rapidfuzz` against the local brand-name table.
- **Matching Engine** never touches the network either. It is pure functions over data already
  in PostgreSQL/Redis. This is the layer that must be fastest and cheapest to run, since every
  user request hits it.
- **RPA / Automation Layer** is the *only* layer allowed to make outbound HTTP requests to
  external pharmacy sites or parse the Jan Aushadhi PDF. It runs on a schedule, writes to
  `price_history`, and never runs inline inside a user's request — a user query always reads
  already-collected data, never triggers a live scrape.
- **API Layer** is a thin orchestrator: validate input → call Matching Engine → read from
  Postgres/Redis → return JSON. It does not contain business logic itself.

## Why this separation matters for the RF course grading

Robot Framework's job in this system is entirely inside the RPA/Automation Layer box. Keeping
that layer physically separate (its own package, its own test suites) means the automation
work — the actual deliverable Robot Framework is graded on — is not tangled inside FastAPI
route handlers where it would be harder to demo or test in isolation.
