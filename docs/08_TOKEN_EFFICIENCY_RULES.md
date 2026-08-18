# Token & Cost Efficiency Rules

This system was designed, top to bottom, to need almost no LLM tokens at runtime — that's a
architectural choice, not an afterthought. This file is the checklist that keeps it that way,
plus the rules for keeping your own build-time context usage lean.

## Runtime: why this system barely calls an LLM at all

Everything a typical "AI-powered" version of this idea would hand to an LLM is deterministic
here instead:

| Task | LLM version (rejected) | This system's version | Why it's cheaper and better |
|---|---|---|---|
| Reading a prescription | Vision-LLM call per image | Tesseract OCR (offline, free) + `rapidfuzz` match | Zero marginal cost per lookup; deterministic, so it's testable with fixed expected outputs |
| Matching salts | "Ask an LLM if these are equivalent" | Normalized tuple-set equality in Postgres | An LLM can hallucinate a "close enough" match on a health-adjacent product — unacceptable; SQL either matches or it doesn't |
| Detecting fake discounts | LLM reads price history and "judges" | SQL window function on `price_history` | Same result, no API call, no latency, no cost per check |
| Ranking substitutes | LLM ranks by "best value" | Fixed rule: `is_jan_aushadhi DESC, price ASC` | Predictable, auditable, free |

**The only place an LLM may ever be introduced** is a *future, optional* fallback: if OCR
confidence is below threshold on a genuinely illegible image, a vision-LLM call could re-attempt
reading it. This is explicitly out of scope for the capstone build — do not add it unless a
later spec file authorizes it. If it's ever added, it must be a single, tightly-scoped call (the
cropped medicine-name region only, not the whole image, not the whole conversation) and its
result must still pass through the same `rapidfuzz` confidence gate as regular OCR output.

## Runtime: other cost controls

- Jan Aushadhi PDF is parsed once and cached — never re-parsed on every scrape run.
- Redis caches salt-lookup results and last-known prices so repeat queries for popular
  medicines don't re-hit Postgres.
- The daily RPA scrape targets one primary source at a fixed, small medicine-category list
  (per `06_FEATURES.md` scope) — not an unbounded catalogue crawl.

## Build-time: keeping the agent's own context usage lean

- Follow `00_AGENT_BRIEF.md`'s file map exactly — open only the spec file the current phase
  needs. Opening all 9 files "for context" at the start of every phase is the single biggest
  waste in a spec-pack build like this.
- Don't paste large file contents back into your own reasoning if you already wrote them this
  session — refer to them by path instead of re-quoting.
- When a phase's DoD fails, report the specific failure and the specific fix, not a full re-walk
  of the phase's reasoning from scratch.
- Keep commit messages and phase reports short and factual (what was built, what passed, what's
  next) — this spec pack is deliberately terse for the same reason; match that register rather
  than padding reports with restated context.
