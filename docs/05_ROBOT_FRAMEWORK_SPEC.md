# Robot Framework & RPA Spec

## Folder Structure (create exactly this)

```
rpa/
├── keywords/
│   ├── scraping_keywords.py       # Open Pharmacy Source, Scrape Medicine Page
│   ├── parsing_keywords.py        # Normalize Salt String, Parse Jan Aushadhi PDF
│   ├── validation_keywords.py     # Validate Price Sanity
│   └── delivery_keywords.py       # Send WhatsApp Digest
├── suites/
│   ├── smoke.robot                # runs before every scheduled scrape
│   ├── data_sanity.robot          # runs after every scrape
│   ├── regression.robot           # runs on every code change
│   └── end_to_end.robot           # runs weekly
├── resources/
│   └── shared.resource            # common variables: URLs, selectors, timeouts
└── scheduler_entry.py             # APScheduler entry point that triggers the daily suite run
```

## Keyword Library (implement these exactly, same names, same signatures)

| Keyword | File | Signature | Behavior |
|---|---|---|---|
| `Open Pharmacy Source` | scraping_keywords.py | `(url: str) -> None` | Launches Browser Library session, sets a realistic user-agent, waits for network idle |
| `Scrape Medicine Page` | scraping_keywords.py | `(product_url: str) -> dict` | Returns `{name, mrp, price, raw_salt_text}`. Raises `ScrapeStructureError` if expected selectors are missing — do not return partial/empty data silently |
| `Normalize Salt String` | parsing_keywords.py | `(raw: str) -> list[tuple[str, float]]` | Pure function, no I/O. Tokenizes, resolves aliases from `salts.aliases`, converts all strengths to mg |
| `Validate Price Sanity` | validation_keywords.py | `(medicine_id: int, new_price: float) -> bool` | Compares against last 7 entries in `price_history`; fails if deviation > 300% with no prior volatility |
| `Match Salt To Substitutes` | (calls Matching Engine, not reimplemented here) | `(medicine_id: int) -> list[dict]` | Thin RF wrapper around the same Python function the API layer calls — **do not duplicate matching logic between RF and FastAPI** |
| `Parse Jan Aushadhi PDF` | parsing_keywords.py | `(pdf_path: str) -> list[dict]` | Uses `RPA.PDF`; returns rows of `{drug_name, salt_text, unit_price}` |
| `Send WhatsApp Digest` | delivery_keywords.py | `(user_id: int, items: list[dict]) -> None` | Calls Twilio; must check `consent_whatsapp` before sending — hard-fail if consent is false, don't just skip silently (that hides a bug) |

## Suite Design

- **smoke.robot** — opens the primary pharmacy source, confirms 2–3 known selectors resolve.
  Runs in under 30 seconds. If it fails, the scheduled full scrape must not run — fail loudly,
  do not fall through.
- **data_sanity.robot** — runs `Validate Price Sanity` against every price written in the
  current scrape batch. Zero or implausible results are a hard failure of the suite, not a
  warning.
- **regression.robot** — fixed table of ~15 known medicine names → expected normalized salt
  output. This is the cheapest, fastest suite (no network) — run it on every commit.
- **end_to_end.robot** — one full path: sample prescription image → OCR → resolve → substitutes
  → savings report. Runs weekly, logs timing.

## Naming & Style Rules

- Keyword names are Title Case with spaces, matching the table above exactly — do not invent
  alternate phrasings across suites.
- Every suite has a `Documentation` field stating what it checks and what "pass" means in one
  sentence — this becomes the demo script.
- No suite may call an LLM. If a step seems to need one, it belongs in a different layer or it
  doesn't belong in this system — flag it rather than adding it here.
