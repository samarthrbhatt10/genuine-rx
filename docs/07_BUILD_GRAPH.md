# Build Graph

Nodes below are the only valid units of work. Each has: inputs it depends on, files it reads,
files it produces, and a Definition of Done that must be true before moving to the next node.
**Stop and report to the user at every ⏸ gate — do not self-approve past it.**

```
P0 ──► P1 ──► P2 ──┬──► P3 ──┐
                    │         ├──► P5 ──► P6 ──► P7
                    └──► P4 ──┘
```

---

### P0 — Repo Scaffold
**Reads:** `01_ARCHITECTURE.md`, `02_TECH_STACK.md`
**Produces:** empty repo with folders matching the architecture layers (`api/`, `rpa/`,
`matching_engine/`, `frontend/`, `alembic/`), `pyproject.toml` / `package.json` with pinned
deps from `02_TECH_STACK.md`, `.env.example`.
**DoD:** `pip install` / `npm install` succeed clean, no version resolution errors.
⏸ **Gate:** confirm folder structure with user before writing any logic.

### P1 — Database
**Reads:** `03_DATA_MODEL.md`
**Produces:** first Alembic migration matching the DDL exactly, seed script with ~15 sample
medicines across 3 salt families (covers the Module A test set needed later).
**DoD:** `alembic upgrade head` runs clean on a fresh database; seed script populates without
FK errors.

### P2 — Matching Engine (pure Python, no I/O)
**Reads:** `06_FEATURES.md` Module B
**Produces:** `matching_engine/` package: salt normalization, alias resolution, mg conversion,
substitute ranking — all pure functions, fully unit tested.
**DoD:** unit tests pass with zero database or network dependency. This is the cheapest node to
get very correct, since P3, P5, and RF all depend on it — do not rush it.

### P3 — RPA / Automation Layer
**Reads:** `05_ROBOT_FRAMEWORK_SPEC.md`, `06_FEATURES.md` Module C
**Depends on:** P1 (writes to real schema), P2 (calls `Match Salt To Substitutes` via the same
matching_engine package — do not reimplement)
**Produces:** full `rpa/` folder per the spec, all four suites, scheduler entry point.
**DoD:** smoke suite passes against the chosen primary pharmacy source; a manual trigger of the
full pipeline writes real rows to `price_history`.
⏸ **Gate:** show a sample scraped + parsed row to the user before wiring the daily schedule live.

### P4 — OCR Resolver
**Reads:** `06_FEATURES.md` Module A
**Depends on:** P2 (fuzzy match uses the same alias tables)
**Produces:** OCR pre-processing + resolution pipeline, standalone, testable without the API.
**DoD:** meets the 80%-confidence bar on the 20-image sample set specified in Module A's DoD.

### P5 — API Layer
**Reads:** `04_API_CONTRACT.md`
**Depends on:** P1, P2, P4
**Produces:** FastAPI app implementing every endpoint in the contract, contract tests.
**DoD:** all contract tests pass against a seeded database.

### P6 — Frontend
**Reads:** `04_API_CONTRACT.md`, `06_FEATURES.md` Module F
**Depends on:** P5
**Produces:** Next.js app — resolve flow, substitute results view, tracked-medicines dashboard.
**DoD:** a full manual walkthrough (upload photo → see savings) works against the real API.

### P7 — Alerts, Analytics, Polish
**Reads:** `06_FEATURES.md` Modules D, E, F
**Depends on:** P3, P5, P6
**Produces:** WhatsApp digest job, monthly report card, trust/safety copy, analytics dashboard.
**DoD:** end_to_end.robot suite passes; a seeded user receives a correct Twilio sandbox digest.
⏸ **Gate:** final review with user before this is called "capstone-demo ready."

---

## Rules for traversing this graph

1. Do not start a node whose dependencies aren't marked done.
2. P3 and P4 can be worked in either order or in parallel — they don't depend on each other,
   only both on P2. Pick whichever the user asks for first.
3. If a node's DoD can't be met, stop and report exactly what's blocking it — don't mark it
   done with a caveat buried in a comment.
