# Data Model — Canonical Source

This is the only place the schema is defined. Every migration must match this file exactly.
If a phase seems to need a column not listed here, stop and flag it — don't add it silently.

## Entity-Relationship Summary

```
salts (1) ---< medicine_salts >--- (1) medicines
medicines (1) ---< price_history
users (1) ---< tracked_medicines >--- (1) medicines
salts (1) ---< caution_list
```

## DDL

```sql
CREATE TABLE salts (
    salt_id       SERIAL PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    aliases       TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE medicines (
    medicine_id   SERIAL PRIMARY KEY,
    brand_name    TEXT NOT NULL,
    form          TEXT NOT NULL,             -- tablet, syrup, capsule, injection
    manufacturer  TEXT,
    is_jan_aushadhi BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_medicines_brand_name ON medicines USING gin (brand_name gin_trgm_ops);

CREATE TABLE medicine_salts (
    medicine_id   INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
    salt_id       INT NOT NULL REFERENCES salts(salt_id) ON DELETE RESTRICT,
    strength_mg   NUMERIC(10,3) NOT NULL,
    PRIMARY KEY (medicine_id, salt_id)
);
CREATE INDEX idx_medicine_salts_salt_strength ON medicine_salts (salt_id, strength_mg);

CREATE TABLE price_history (
    id            BIGSERIAL PRIMARY KEY,
    medicine_id   INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
    source        TEXT NOT NULL,             -- 'primary_pharmacy' | 'jan_aushadhi_pdf'
    price         NUMERIC(10,2) NOT NULL,
    scraped_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- append-only: no UPDATE or DELETE permission granted to the API role, only INSERT + SELECT
CREATE INDEX idx_price_history_medicine_time ON price_history (medicine_id, scraped_at DESC);

CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    phone         TEXT NOT NULL UNIQUE,
    consent_whatsapp BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tracked_medicines (
    id            SERIAL PRIMARY KEY,
    user_id       INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    medicine_id   INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
    profile_label TEXT NOT NULL DEFAULT 'self',   -- e.g. 'self', 'Amma', 'Papa'
    UNIQUE (user_id, medicine_id, profile_label)
);

CREATE TABLE caution_list (
    salt_id       INT PRIMARY KEY REFERENCES salts(salt_id) ON DELETE CASCADE,
    reason        TEXT NOT NULL      -- e.g. 'narrow therapeutic index — thyroid'
);
```

## Rules

1. `price_history` is append-only. The API role must not have `UPDATE`/`DELETE` grants on it —
   enforce this in the migration, not just by convention.
2. `medicine_salts.strength_mg` is always normalized to milligrams before insert — conversion
   happens in the Matching Engine (see `06_FEATURES.md`), never store raw "0.5g" style strings.
3. Every schema change is a new Alembic migration file. No manual `ALTER TABLE` against the
   running database, including in development.
4. `salts.aliases` holds known abbreviations/misspellings (e.g. `{'PCM', 'Paracetamol Tab'}`
   for canonical `Paracetamol`) — this table grows over the project's life; seed it small and
   expand it as OCR mismatches are found during testing, per `06_FEATURES.md` Module A.
