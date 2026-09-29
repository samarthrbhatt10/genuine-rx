"""
price_alert_bot.py — RPA Automation: Price-Drop & Jan Aushadhi Alert Bot.

For every user it checks their tracked medicines and emails ONE digest when:
  1. PRICE DROP     — the latest price_history row is lower than the previous one.
  2. JAN AUSHADHI   — a cheaper Jan Aushadhi medicine with the identical salt
                      composition + strength exists for a branded tracked medicine.

Each alert is sent once (alert_log dedupes), so running the bot nightly never
spams the user.

CLI (run from repo root):
    python -m rpa.alerts.price_alert_bot                      # detect + send
    python -m rpa.alerts.price_alert_bot --dry-run            # detect only
    python -m rpa.alerts.price_alert_bot --simulate-drop Crocin --pct 20
    python -m rpa.alerts.price_alert_bot --reset              # forget sent alerts
    python -m rpa.alerts.price_alert_bot --set-email 1 me@gmail.com
    python -m rpa.alerts.price_alert_bot --test-email me@gmail.com

Environment (all optional — see .env.example):
    GENUINE_RX_DB_URL              database (falls back to the local dev DB)
    GENUINE_RX_ALERT_TO_EMAIL      demo override: every alert goes to this address
    GENUINE_RX_ALERT_MIN_DROP_PCT  ignore drops smaller than this (default 0.5)
    GENUINE_RX_SMTP_*              see mailer.py (no SMTP -> saved to rpa/outbox/)
"""
import argparse
import html
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from rpa.alerts.mailer import MailError, send_email, smtp_configured  # noqa: E402

try:  # python-dotenv is already used by the API; optional here
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:  # pragma: no cover
    pass

log = logging.getLogger("genuine_rx.alerts")

DROP = "price_drop"
JAN_AUSHADHI = "jan_aushadhi"
_DEFAULT_DSN = "postgresql://postgres:devpass@localhost:5433/genuine_rx"  # same as api/database.py


# --------------------------------------------------------------------------- #
# DB helpers
# --------------------------------------------------------------------------- #

def connect() -> psycopg.Connection:
    dsn = os.environ.get("GENUINE_RX_DB_URL", _DEFAULT_DSN).replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=True)


def ensure_schema(conn: psycopg.Connection) -> None:
    """Idempotent — same DDL as alembic migration 0002."""
    conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_log (
            id          BIGSERIAL PRIMARY KEY,
            user_id     INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            medicine_id INT NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
            alert_type  TEXT NOT NULL,
            dedupe_key  TEXT NOT NULL,
            sent_to     TEXT NOT NULL,
            sent_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (user_id, medicine_id, alert_type, dedupe_key)
        )
    """)


def set_user_email(conn: psycopg.Connection, user_id: int, email: str) -> None:
    ensure_schema(conn)
    cur = conn.execute("UPDATE users SET email = %s WHERE user_id = %s", (email, user_id))
    if cur.rowcount == 0:
        raise ValueError(f"User {user_id} not found.")


def reset_alert_log(conn: psycopg.Connection) -> None:
    ensure_schema(conn)
    conn.execute("DELETE FROM alert_log")


# --------------------------------------------------------------------------- #
# Detection
# --------------------------------------------------------------------------- #

_PRICE_DROPS_SQL = """
WITH ranked AS (
    SELECT id, medicine_id, price,
           ROW_NUMBER() OVER (PARTITION BY medicine_id ORDER BY scraped_at DESC, id DESC) AS rn
      FROM price_history
)
SELECT t.user_id, t.medicine_id, t.profile_label, m.brand_name,
       cur.id AS price_id, cur.price AS new_price, prev.price AS old_price
  FROM tracked_medicines t
  JOIN medicines m USING (medicine_id)
  JOIN ranked cur  ON cur.medicine_id  = t.medicine_id AND cur.rn  = 1
  JOIN ranked prev ON prev.medicine_id = t.medicine_id AND prev.rn = 2
 WHERE cur.price < prev.price
"""

# Same salts + same strengths <=> identical "signature". Mirrors the matching
# engine's salt-set equivalence, expressed in SQL so the bot needs no API.
_JAN_AUSHADHI_SQL = """
WITH sig AS (
    SELECT medicine_id,
           array_agg(salt_id::text || ':' || strength_mg::text ORDER BY salt_id) AS signature
      FROM medicine_salts GROUP BY medicine_id
),
latest AS (
    SELECT DISTINCT ON (medicine_id) medicine_id, price
      FROM price_history ORDER BY medicine_id, scraped_at DESC, id DESC
)
SELECT t.user_id, t.medicine_id, t.profile_label, m.brand_name, bp.price AS brand_price,
       ja.medicine_id AS ja_medicine_id, ja.brand_name AS ja_name, jp.price AS ja_price,
       EXISTS (SELECT 1 FROM medicine_salts ms JOIN caution_list c USING (salt_id)
                WHERE ms.medicine_id = t.medicine_id) AS caution
  FROM tracked_medicines t
  JOIN medicines m USING (medicine_id)
  JOIN sig s1 ON s1.medicine_id = t.medicine_id
  JOIN sig s2 ON s2.signature = s1.signature
  JOIN medicines ja ON ja.medicine_id = s2.medicine_id AND ja.is_jan_aushadhi
  JOIN latest bp ON bp.medicine_id = t.medicine_id
  JOIN latest jp ON jp.medicine_id = ja.medicine_id
 WHERE NOT m.is_jan_aushadhi AND jp.price < bp.price
"""


def find_price_drops(conn: psycopg.Connection, min_drop_pct: float) -> list[dict]:
    alerts = []
    for r in conn.execute(_PRICE_DROPS_SQL).fetchall():
        old, new = Decimal(r["old_price"]), Decimal(r["new_price"])
        pct = float((old - new) / old * 100)
        if pct < min_drop_pct:
            continue
        alerts.append({
            "type": DROP, "user_id": r["user_id"], "medicine_id": r["medicine_id"],
            "brand_name": r["brand_name"], "profile_label": r["profile_label"],
            "old_price": float(old), "new_price": float(new), "drop_pct": round(pct, 1),
            "dedupe_key": str(r["price_id"]),
        })
    return alerts


def find_jan_aushadhi_options(conn: psycopg.Connection) -> list[dict]:
    alerts = []
    for r in conn.execute(_JAN_AUSHADHI_SQL).fetchall():
        brand, ja = Decimal(r["brand_price"]), Decimal(r["ja_price"])
        alerts.append({
            "type": JAN_AUSHADHI, "user_id": r["user_id"], "medicine_id": r["medicine_id"],
            "brand_name": r["brand_name"], "profile_label": r["profile_label"],
            "brand_price": float(brand), "ja_name": r["ja_name"], "ja_price": float(ja),
            "save_rupees": float(brand - ja), "save_pct": round(float((brand - ja) / brand * 100), 1),
            "caution": r["caution"], "dedupe_key": str(r["ja_medicine_id"]),
        })
    return alerts


def _filter_already_sent(conn: psycopg.Connection, alerts: list[dict]) -> list[dict]:
    sent = {
        (r["user_id"], r["medicine_id"], r["alert_type"], r["dedupe_key"])
        for r in conn.execute("SELECT user_id, medicine_id, alert_type, dedupe_key FROM alert_log").fetchall()
    }
    return [a for a in alerts if (a["user_id"], a["medicine_id"], a["type"], a["dedupe_key"]) not in sent]


# --------------------------------------------------------------------------- #
# Email content
# --------------------------------------------------------------------------- #

_DISCLAIMER = "Always confirm any substitute with your doctor or pharmacist before switching."


def _who(a: dict) -> str:
    return "" if a["profile_label"] == "self" else f" (for {a['profile_label']})"


def build_email(alerts: list[dict]) -> tuple[str, str, str]:
    """Returns (subject, html, plain_text) for one user's alerts."""
    drops = [a for a in alerts if a["type"] == DROP]
    jans = [a for a in alerts if a["type"] == JAN_AUSHADHI]

    if drops:
        d = max(drops, key=lambda a: a["drop_pct"])
        subject = f"Price drop: {d['brand_name']} is now Rs.{d['new_price']:.2f} (-{d['drop_pct']}%)"
        if len(alerts) > 1:
            subject += f" + {len(alerts) - 1} more update(s)"
    else:
        j = max(jans, key=lambda a: a["save_rupees"])
        subject = f"Save Rs.{j['save_rupees']:.2f}: Jan Aushadhi alternative for {j['brand_name']}"

    text, rows_html = [], []
    if drops:
        text.append("PRICE DROPS")
        rows_html.append("<h3 style='color:#166534'>&#128201; Price drops on your tracked medicines</h3><ul>")
        for a in drops:
            line = f"{a['brand_name']}{_who(a)}: Rs.{a['old_price']:.2f} -> Rs.{a['new_price']:.2f} (-{a['drop_pct']}%)"
            text.append(f"  - {line}")
            rows_html.append(f"<li><b>{html.escape(a['brand_name'])}</b>{html.escape(_who(a))}: "
                             f"<s>Rs.{a['old_price']:.2f}</s> &rarr; <b>Rs.{a['new_price']:.2f}</b> "
                             f"<span style='color:#166534'>(-{a['drop_pct']}%)</span></li>")
        rows_html.append("</ul>")
    if jans:
        text.append("JAN AUSHADHI ALTERNATIVES")
        rows_html.append("<h3 style='color:#1d4ed8'>&#128138; Cheaper Jan Aushadhi alternative available</h3><ul>")
        for a in jans:
            line = (f"{a['brand_name']}{_who(a)} Rs.{a['brand_price']:.2f} -> {a['ja_name']} "
                    f"Rs.{a['ja_price']:.2f}: save Rs.{a['save_rupees']:.2f} ({a['save_pct']}%)")
            text.append(f"  - {line}")
            warn = ""
            if a["caution"]:
                text.append("    CAUTION: narrow-therapeutic-index / high-risk salt - consult your doctor before switching.")
                warn = "<br><span style='color:#b91c1c'>&#9888; Caution: high-risk salt &mdash; consult your doctor before switching.</span>"
            rows_html.append(f"<li><b>{html.escape(a['brand_name'])}</b>{html.escape(_who(a))} "
                             f"Rs.{a['brand_price']:.2f} &rarr; <b>{html.escape(a['ja_name'])}</b> "
                             f"Rs.{a['ja_price']:.2f} &mdash; save <b>Rs.{a['save_rupees']:.2f}</b> "
                             f"({a['save_pct']}%){warn}</li>")
        rows_html.append("</ul>")

    text += ["", _DISCLAIMER, "-- Genuine RX automated price alerts"]
    body = (
        "<div style='font-family:Arial,sans-serif;max-width:560px;margin:auto;border:1px solid #e5e7eb;"
        "border-radius:8px;padding:20px'>"
        "<h2 style='margin-top:0'>&#128138; Genuine RX &mdash; Price Alert</h2>"
        + "".join(rows_html)
        + f"<p style='color:#6b7280;font-size:12px'>{_DISCLAIMER}<br>Sent automatically by the Genuine RX RPA alert bot.</p></div>"
    )
    return subject, body, "\n".join(text)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def run_alert_bot(conn: psycopg.Connection | None = None, dry_run: bool = False) -> dict:
    """Detect new alerts and email each user one digest.

    Returns a summary dict: drops, jan_aushadhi, emails (list), skipped, errors.
    """
    own_conn = conn is None
    conn = conn or connect()
    try:
        ensure_schema(conn)
        min_pct = float(os.environ.get("GENUINE_RX_ALERT_MIN_DROP_PCT", "0.5"))
        override_to = os.environ.get("GENUINE_RX_ALERT_TO_EMAIL", "").strip()

        alerts = _filter_already_sent(conn, find_price_drops(conn, min_pct) + find_jan_aushadhi_options(conn))
        summary = {
            "drops": sum(a["type"] == DROP for a in alerts),
            "jan_aushadhi": sum(a["type"] == JAN_AUSHADHI for a in alerts),
            "emails": [], "skipped": [], "errors": [], "dry_run": dry_run,
        }

        by_user: dict[int, list[dict]] = {}
        for a in alerts:
            by_user.setdefault(a["user_id"], []).append(a)

        for user_id, user_alerts in by_user.items():
            row = conn.execute("SELECT phone, email FROM users WHERE user_id = %s", (user_id,)).fetchone()
            to = override_to or (row["email"] or "").strip()
            if not to and not smtp_configured():
                to = f"user{user_id}@demo.local"  # demo mode: nothing is really sent, file goes to rpa/outbox/
            if not to:
                summary["skipped"].append({"user_id": user_id, "reason": "no email on file and GENUINE_RX_ALERT_TO_EMAIL not set"})
                log.warning("User %s has %d alert(s) but no email — skipped.", user_id, len(user_alerts))
                continue

            subject, html_body, text_body = build_email(user_alerts)
            entry = {"user_id": user_id, "to": to, "subject": subject, "alerts": len(user_alerts),
                     "text": text_body, "mode": "dry-run", "path": None}
            if not dry_run:
                try:
                    entry.update(send_email(to, subject, html_body, text_body))
                except MailError as exc:
                    summary["errors"].append(str(exc))
                    log.error("%s", exc)
                    continue  # not logged as sent -> retried on the next run
                with conn.transaction():
                    for a in user_alerts:
                        conn.execute(
                            "INSERT INTO alert_log (user_id, medicine_id, alert_type, dedupe_key, sent_to) "
                            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                            (a["user_id"], a["medicine_id"], a["type"], a["dedupe_key"], to),
                        )
            summary["emails"].append(entry)
            log.info("Alert email (%s) -> %s: %s", entry["mode"], to, subject)
        return summary
    finally:
        if own_conn:
            conn.close()


def simulate_price_drop(conn: psycopg.Connection, brand_name: str | None = None, pct: float = 20.0) -> dict:
    """Demo helper: append a new, lower price_history row for a tracked medicine.

    Simulates the nightly scraper discovering a cheaper price. price_history is
    append-only, so this is a plain INSERT.
    """
    row = conn.execute(
        """
        SELECT m.medicine_id, m.brand_name,
               (SELECT ph.price  FROM price_history ph WHERE ph.medicine_id = m.medicine_id ORDER BY scraped_at DESC, id DESC LIMIT 1) AS price,
               (SELECT ph.source FROM price_history ph WHERE ph.medicine_id = m.medicine_id ORDER BY scraped_at DESC, id DESC LIMIT 1) AS source
          FROM medicines m
         WHERE m.medicine_id IN (SELECT medicine_id FROM tracked_medicines)
           AND (%(b)s::text IS NULL OR m.brand_name ILIKE %(b)s)
         ORDER BY m.medicine_id LIMIT 1
        """,
        {"b": brand_name},
    ).fetchone()
    if not row or row["price"] is None:
        raise ValueError(f"No tracked medicine with a price found for {brand_name!r}.")
    new_price = (Decimal(row["price"]) * (Decimal(100) - Decimal(str(pct))) / 100).quantize(Decimal("0.01"))
    conn.execute(
        "INSERT INTO price_history (medicine_id, source, price) VALUES (%s, %s, %s)",
        (row["medicine_id"], row["source"], new_price),
    )
    return {"medicine_id": row["medicine_id"], "brand_name": row["brand_name"],
            "old_price": float(row["price"]), "new_price": float(new_price)}


def send_test_email(to: str) -> dict:
    return send_email(
        to, "Genuine RX — test email",
        "<h3>Genuine RX alert bot is configured correctly &#9989;</h3>",
        "Genuine RX alert bot is configured correctly.",
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _print_summary(s: dict) -> None:
    print(f"\nNew alerts: {s['drops']} price drop(s), {s['jan_aushadhi']} Jan Aushadhi option(s)")
    for e in s["emails"]:
        where = e["path"] or e["to"]
        print(f"  [{e['mode']}] user {e['user_id']} -> {e['to']}: {e['subject']}")
        if e["mode"] == "outbox":
            print(f"      open: {where}")
    for sk in s["skipped"]:
        print(f"  [skipped] user {sk['user_id']}: {sk['reason']}")
    for err in s["errors"]:
        print(f"  [ERROR] {err}")
    if not (s["emails"] or s["skipped"] or s["errors"]):
        print("  Nothing new to send (already alerted). Use --simulate-drop or --reset for the demo.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Genuine RX price-drop / Jan Aushadhi email alert bot")
    ap.add_argument("--dry-run", action="store_true", help="detect alerts but don't send or record them")
    ap.add_argument("--simulate-drop", nargs="?", const="", metavar="BRAND",
                    help="insert a lower price for a tracked medicine (default: first tracked)")
    ap.add_argument("--pct", type=float, default=20.0, help="drop size for --simulate-drop (default 20)")
    ap.add_argument("--reset", action="store_true", help="clear alert_log so alerts fire again")
    ap.add_argument("--set-email", nargs=2, metavar=("USER_ID", "EMAIL"))
    ap.add_argument("--test-email", metavar="EMAIL", help="send a test email to verify SMTP settings")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.test_email:
        print("Test email:", send_test_email(args.test_email))
        return 0

    with connect() as conn:
        if args.set_email:
            set_user_email(conn, int(args.set_email[0]), args.set_email[1])
            print(f"Email for user {args.set_email[0]} set to {args.set_email[1]}")
            return 0
        if args.reset:
            reset_alert_log(conn)
            print("alert_log cleared.")
        if args.simulate_drop is not None:
            ensure_schema(conn)
            d = simulate_price_drop(conn, args.simulate_drop or None, args.pct)
            print(f"Simulated scrape: {d['brand_name']} Rs.{d['old_price']:.2f} -> Rs.{d['new_price']:.2f}")
        _print_summary(run_alert_bot(conn, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
