"""Initial schema — all tables, indexes, role grants.

Matches 03_DATA_MODEL.md exactly. No column or index may be added here
without a corresponding update to that spec file.

Revision ID: 0001
Revises:
Create Date: 2026-08-05
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Extensions
    # ------------------------------------------------------------------ #
    # pg_trgm is required for the GIN trigram index on medicines.brand_name.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # ------------------------------------------------------------------ #
    # salts
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE salts (
            salt_id       SERIAL PRIMARY KEY,
            canonical_name TEXT NOT NULL UNIQUE,
            aliases       TEXT[] NOT NULL DEFAULT '{}'
        );
    """)

    # ------------------------------------------------------------------ #
    # medicines
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE medicines (
            medicine_id     SERIAL PRIMARY KEY,
            brand_name      TEXT NOT NULL,
            form            TEXT NOT NULL,
            manufacturer    TEXT,
            is_jan_aushadhi BOOLEAN NOT NULL DEFAULT FALSE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    # GIN trigram index — enables fast ILIKE / similarity search on brand_name
    op.execute("""
        CREATE INDEX idx_medicines_brand_name
            ON medicines USING gin (brand_name gin_trgm_ops);
    """)

    # ------------------------------------------------------------------ #
    # medicine_salts  (junction table)
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE medicine_salts (
            medicine_id  INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
            salt_id      INT NOT NULL REFERENCES salts(salt_id) ON DELETE RESTRICT,
            strength_mg  NUMERIC(10,3) NOT NULL,
            PRIMARY KEY (medicine_id, salt_id)
        );
    """)
    op.execute("""
        CREATE INDEX idx_medicine_salts_salt_strength
            ON medicine_salts (salt_id, strength_mg);
    """)

    # ------------------------------------------------------------------ #
    # price_history  (append-only — enforced by role grants below)
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE price_history (
            id          BIGSERIAL PRIMARY KEY,
            medicine_id INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
            source      TEXT NOT NULL,
            price       NUMERIC(10,2) NOT NULL,
            scraped_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("""
        CREATE INDEX idx_price_history_medicine_time
            ON price_history (medicine_id, scraped_at DESC);
    """)

    # ------------------------------------------------------------------ #
    # users
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE users (
            user_id          SERIAL PRIMARY KEY,
            phone            TEXT NOT NULL UNIQUE,
            consent_whatsapp BOOLEAN NOT NULL DEFAULT FALSE,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # ------------------------------------------------------------------ #
    # tracked_medicines
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE tracked_medicines (
            id            SERIAL PRIMARY KEY,
            user_id       INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            medicine_id   INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
            profile_label TEXT NOT NULL DEFAULT 'self',
            UNIQUE (user_id, medicine_id, profile_label)
        );
    """)

    # ------------------------------------------------------------------ #
    # caution_list
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE caution_list (
            salt_id INT PRIMARY KEY REFERENCES salts(salt_id) ON DELETE CASCADE,
            reason  TEXT NOT NULL
        );
    """)

    # ------------------------------------------------------------------ #
    # API role — price_history is append-only per 03_DATA_MODEL.md rule 1
    # ------------------------------------------------------------------ #
    # Create role only if it doesn't already exist (idempotent).
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'genuine_rx_api') THEN
                CREATE ROLE genuine_rx_api NOLOGIN;
            END IF;
        END
        $$;
    """)
    # Grant SELECT + INSERT on price_history — explicitly no UPDATE / DELETE.
    op.execute("""
        GRANT SELECT, INSERT ON price_history TO genuine_rx_api;
    """)
    # Full read/write on all other tables for the API role.
    op.execute("""
        GRANT SELECT, INSERT, UPDATE, DELETE
            ON salts, medicines, medicine_salts, users, tracked_medicines, caution_list
            TO genuine_rx_api;
    """)
    # Sequence access so SERIAL columns work.
    op.execute("""
        GRANT USAGE, SELECT
            ON ALL SEQUENCES IN SCHEMA public
            TO genuine_rx_api;
    """)


def downgrade() -> None:
    # Drop in reverse dependency order.
    op.execute("DROP TABLE IF EXISTS caution_list CASCADE;")
    op.execute("DROP TABLE IF EXISTS tracked_medicines CASCADE;")
    op.execute("DROP TABLE IF EXISTS price_history CASCADE;")
    op.execute("DROP TABLE IF EXISTS medicine_salts CASCADE;")
    op.execute("DROP TABLE IF EXISTS medicines CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
    op.execute("DROP TABLE IF EXISTS salts CASCADE;")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
