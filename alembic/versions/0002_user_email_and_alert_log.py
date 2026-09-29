"""Add users.email and alert_log (dedupe table for the price-drop alert bot).

Both statements are idempotent — the alert bot also runs them on start-up
(rpa/alerts/price_alert_bot.py::ensure_schema), so either path works.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-29
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;")
    op.execute("""
        CREATE TABLE IF NOT EXISTS alert_log (
            id          BIGSERIAL PRIMARY KEY,
            user_id     INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            medicine_id INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
            alert_type  TEXT NOT NULL,
            dedupe_key  TEXT NOT NULL,
            sent_to     TEXT NOT NULL,
            sent_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (user_id, medicine_id, alert_type, dedupe_key)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS alert_log;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email;")
