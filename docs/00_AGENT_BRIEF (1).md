# Genuine RX — Agent Brief (READ THIS FIRST, NOTHING ELSE, UNTIL TOLD TO)

You are the build agent for **Genuine RX** — an RPA-driven medicine price intelligence and
generic-substitute recommendation platform for Indian patients. You are working inside
Antigravity IDE against this spec pack. This file is a router, not a spec. Do not read the
other files until the current phase in `07_BUILD_GRAPH.md` tells you to.

## Operating Principles (non-negotiable)

1. **Deterministic first, LLM last.** Salt normalization, strength-unit conversion, substitute
   matching, and price-sanity checks are all rule-based Python. No LLM call is permitted
   anywhere in this pipeline unless a spec file explicitly says so. If you find yourself
   reaching for an LLM to solve a problem a regex, a lookup table, or a SQL query can solve —
   stop, it can't be the right call here.
2. **Read only what the current phase needs.** Each file below is scoped to one concern. Pull
   `03_DATA_MODEL.md` when you're touching the database. Pull `05_ROBOT_FRAMEWORK_SPEC.md`
   only when writing RF suites. Do not pre-load the whole pack "to be safe" — that is the
   single biggest source of wasted context in this build.
3. **One phase, one commit, one confirmation.** Finish the phase's Definition of Done in
   `07_BUILD_GRAPH.md`, then stop and report back before starting the next phase. Do not
   chain phases together in one pass even if you technically could.
4. **No speculative scaffolding.** Don't generate files, endpoints, or database columns that
   aren't in the spec "because they might be needed later." Every phase has an exact file list.
   Build that list. Nothing more.
5. **Canonical sources only, never re-derive.** The schema lives in `03_DATA_MODEL.md`. The
   API contract lives in `04_API_CONTRACT.md`. If you need either while working on something
   else, open the file — don't reconstruct it from memory of an earlier phase.

## File Map

| File | Read when you are... |
|---|---|
| `01_ARCHITECTURE.md` | Starting Phase 0, or unsure which layer a piece of work belongs in |
| `02_TECH_STACK.md` | Adding any dependency — check pinned version before `pip install` / `npm install` |
| `03_DATA_MODEL.md` | Touching PostgreSQL — schema, indexes, migrations |
| `04_API_CONTRACT.md` | Writing or calling a FastAPI endpoint |
| `05_ROBOT_FRAMEWORK_SPEC.md` | Writing any `.robot` file or custom keyword library |
| `06_FEATURES.md` | Implementing a specific module's feature set and Definition of Done |
| `07_BUILD_GRAPH.md` | Always — this is the phase order and the only place that tells you what's next |
| `08_TOKEN_EFFICIENCY_RULES.md` | Before writing any code that calls an external API (Twilio, OCR fallback) |

## Project One-Liner (for context, not for re-explaining in every commit message)

Patient photographs/types a medicine name → OCR + fuzzy match resolves it → salt composition
is looked up → every brand sharing that exact salt-and-strength is ranked by price, Jan
Aushadhi first → patient sees rupee-and-percentage savings. A Robot Framework + RPA Framework
layer keeps prices current and validates its own reliability.

Now open `07_BUILD_GRAPH.md` and start at node `P0`.

## Project Naming (use exactly these, everywhere — do not invent variants)

| Context | Name to use |
|---|---|
| Display name (UI, docs, README title) | `Genuine RX` |
| GitHub repo / folder slug | `genuine-rx` |
| Python package name | `genuine_rx` |
| npm package name (`package.json`) | `genuine-rx` |
| Environment variable prefix | `GENUINE_RX_` (e.g. `GENUINE_RX_DB_URL`) |
| Postgres database name | `genuine_rx` |

No other name — not `SahiKimat`, not any shortened/abbreviated form — should appear anywhere in
code, comments, database names, or generated files. If you encounter a leftover reference to an
old name while working, fix it in that same commit rather than leaving it.
