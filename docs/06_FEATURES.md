# Features by Module — with Definition of Done

Each module below is a self-contained unit of work. Do not start a module until its dependency
(listed in `07_BUILD_GRAPH.md`) is done.

## Module A — Prescription & Medicine Resolver

- [ ] Image pre-processing pipeline: deskew + CLAHE contrast normalization (OpenCV) before OCR
- [ ] Tesseract OCR call, offline, no network
- [ ] `rapidfuzz` match against `medicines.brand_name` (+ `salts.aliases`), threshold-gated
      per `04_API_CONTRACT.md`
- [ ] **Delight feature:** barcode/strip-photo shortcut — if a clean barcode is detected in the
      image (OpenCV barcode detector), skip OCR entirely and look up by known barcode-to-brand
      table. Cheaper and more accurate than OCR when available; falls back to OCR if not found.
- **DoD:** given 20 sample prescription photos (mixed handwriting quality), correctly resolves
  ≥ 80% at high confidence, and correctly flags the rest as needs-confirmation rather than
  guessing wrong silently.

## Module B — Generic Substitute Engine (Matching Engine)

- [ ] Salt normalization (alias resolution + mg conversion) as pure functions — reused by both
      FastAPI and Robot Framework, defined once in `matching_engine/` package
- [ ] Order-independent salt-set matching for combination drugs
- [ ] Ranking: `is_jan_aushadhi DESC, price ASC` (fixed, per API contract)
- [ ] Caution-list check runs on every substitute lookup, not as an afterthought
- **DoD:** unit tests cover single-salt, multi-salt combination, and zero-match cases; all pass
  with no network or database mocking beyond a test fixture.

## Module C — RPA Price Intelligence

- [ ] Daily scheduled Robot Framework run (see `05_ROBOT_FRAMEWORK_SPEC.md`)
- [ ] Jan Aushadhi PDF parsed once at setup, re-parsed only when a new list is published
      (not on every run — this is a static-ish source, don't re-fetch it daily)
- [ ] **Delight feature:** fake-discount flag — once ≥ 14 days of `price_history` exist for a
      medicine, flag any "sale" where the pre-sale price spiked > 20% in the prior 3 days. Pure
      SQL window-function query, no ML needed for this.
- **DoD:** a full scheduled run completes, writes to `price_history`, and the smoke + data-
  sanity suites both pass on that run.

## Module D — Savings, Alerts & Family Profiles

- [ ] Savings calculation (₹ and %) computed at query time from `price_history`, not stored
      redundantly
- [ ] WhatsApp digest: weekly for tracked medicines, includes any price change since last digest
- [ ] Family profiles via `tracked_medicines.profile_label`
- [ ] **Delight feature:** monthly "spend report card" — one WhatsApp message per month summing
      total realized savings across all tracked medicines for that user. Cheap to compute
      (single aggregate SQL query), high perceived value.
- **DoD:** a seeded test user with 3 tracked medicines receives a correctly formatted digest via
  Twilio's sandbox mode.

## Module E — Trust & Safety

- [ ] Every substitute response includes a static disclaimer string (confirm with
      pharmacist/doctor)
- [ ] Caution list checked and surfaced per Module B
- [ ] Exact-match-only enforced at the query level (no "similar salt" fallback, ever)
- **DoD:** attempting to fetch substitutes for a medicine on the caution list returns a non-null
  `caution_flag` in every response, verified by an automated test, not manual inspection.

## Module F — Analytics

- [ ] Dashboard: cumulative savings, price-history trend chart per tracked medicine
- [ ] Built from existing `price_history` + `tracked_medicines` — no new tables needed
- **DoD:** dashboard renders correctly for a seeded user with ≥ 2 weeks of price history.

## Module G — API & Serving Layer

- [ ] Implements exactly the endpoints in `04_API_CONTRACT.md`, no more, no fewer
- [ ] Input validation via Pydantic models matching the contract's request shapes exactly
- **DoD:** contract tests (one per endpoint) pass against a seeded test database.
