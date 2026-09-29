"""
scheduler_entry.py — APScheduler entry point for the daily RPA pipeline.

Usage:
    python rpa/scheduler_entry.py

The scheduler runs the following pipeline daily (default: 02:30 IST / 21:00 UTC):
  1. smoke.robot  — gates the scrape; aborts if it fails.
  2. Full scrape  — calls Scrape Medicine Page for each tracked medicine URL.
  3. Writes rows  — inserts new price_history entries.
  4. data_sanity.robot — validates all prices just written; logs failures.
  5. Alert bot    — emails users about price drops / Jan Aushadhi options.

The regression.robot suite is NOT run here — it's a CI gate (run on commit).
The end_to_end.robot suite is NOT run here — it runs weekly via a separate job.

Requires:
  - GENUINE_RX_DB_URL set in environment.
  - GENUINE_RX_SCRAPE_CRON set (default: "30 21 * * *" = 02:30 IST).
  - Python 3.11 venv with requirements-rpa.txt installed + `rfbrowser init`.
"""
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path

# ---- APScheduler -----------------------------------------------------------
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# ---- Robot Framework runner ------------------------------------------------
from robot import run as robot_run

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

import psycopg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("genuine_rx.scheduler")

_SUITES_DIR = Path(__file__).parent / "suites"
_DB_URL     = os.environ.get("GENUINE_RX_DB_URL", "")
_CRON       = os.environ.get("GENUINE_RX_SCRAPE_CRON", "30 21 * * *")


# --------------------------------------------------------------------------- #
# Pipeline steps
# --------------------------------------------------------------------------- #

def _run_smoke() -> bool:
    """Run smoke.robot. Returns True if all tests passed."""
    rc = robot_run(
        str(_SUITES_DIR / "smoke.robot"),
        outputdir="rpa/logs/smoke",
        loglevel="INFO",
    )
    return rc == 0


def _scrape_all_medicines() -> list[dict]:
    """Scrape price for every medicine in the database.

    Returns a list of dicts {medicine_id, brand_name, new_price, source}
    for all successfully scraped medicines.

    In a production implementation, each medicine would have a
    stored product_url in the medicines table (added via a future migration).
    For now this demonstrates the pipeline structure.
    """
    from rpa.keywords.scraping_keywords import ScrapingKeywords, ScrapeStructureError

    dsn = _DB_URL.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn) as conn:
        meds = conn.execute(
            "SELECT medicine_id, brand_name FROM medicines"
        ).fetchall()

    # TODO (P3 enhancement): store product_url per medicine and iterate over it.
    # For the initial pipeline demo, we scrape the smoke product URL as a sample.
    scraper = ScrapingKeywords()
    batch: list[dict] = []

    from rpa.resources import shared  # noqa: F401 — shared constants live in shared.resource
    SMOKE_URL = "https://www.1mg.com/drugs/crocin-500mg-tablet-5960"

    try:
        scraper.open_pharmacy_source("https://www.1mg.com")
        data = scraper.scrape_medicine_page(SMOKE_URL)
        # The scraped medicine corresponds to medicine_id 1 (Crocin) in the seed.
        batch.append({
            "medicine_id": 16,          # Crocin in seeded DB (id from seed run)
            "brand_name":  data["name"],
            "new_price":   float(data["price"].replace("Rs.", "").replace(",", "").strip()),
            "source":      "primary_pharmacy",
        })
    except ScrapeStructureError as exc:
        log.error(f"Scrape failed: {exc}")

    return batch


def _write_price_history(batch: list[dict]) -> None:
    """Insert scraped prices into price_history (append-only)."""
    dsn = _DB_URL.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn, autocommit=False) as conn:
        for item in batch:
            conn.execute(
                "INSERT INTO price_history (medicine_id, source, price) VALUES (%s, %s, %s)",
                (item["medicine_id"], item["source"], Decimal(str(item["new_price"]))),
            )
        conn.commit()
    log.info(f"Wrote {len(batch)} price_history rows.")


def _run_data_sanity(batch: list[dict]) -> bool:
    """Run data_sanity.robot with the scraped batch injected as a variable."""
    rc = robot_run(
        str(_SUITES_DIR / "data_sanity.robot"),
        outputdir="rpa/logs/data_sanity",
        variable=[f"SCRAPE_BATCH:{batch}"],
        loglevel="INFO",
    )
    return rc == 0


# --------------------------------------------------------------------------- #
# Main pipeline job
# --------------------------------------------------------------------------- #

def run_daily_pipeline() -> None:
    """Full daily scrape pipeline — called by APScheduler."""
    log.info("=== Daily pipeline starting ===")

    # Step 1: smoke gate
    log.info("Step 1/5: Running smoke suite…")
    if not _run_smoke():
        log.error("Smoke suite FAILED — aborting scrape. Check rpa/logs/smoke/.")
        return

    log.info("Step 2/5: Scraping medicine prices…")
    batch = _scrape_all_medicines()
    if not batch:
        log.error("No prices scraped — aborting pipeline.")
        return

    log.info(f"Step 3/5: Writing {len(batch)} rows to price_history…")
    _write_price_history(batch)

    log.info("Step 4/5: Running data sanity suite…")
    sanity_ok = _run_data_sanity(batch)
    if not sanity_ok:
        log.error("Data sanity FAILED — prices written but flagged. Review rpa/logs/data_sanity/.")
    else:
        log.info("=== Daily pipeline completed successfully ===")

    # Step 5: alert users — skipped when sanity failed so bad data never reaches an inbox.
    if sanity_ok:
        log.info("Step 5/5: Sending price-drop / Jan Aushadhi alerts…")
        try:
            from rpa.alerts.price_alert_bot import run_alert_bot
            s = run_alert_bot()
            log.info(f"Alerts: {s['drops']} drop(s), {s['jan_aushadhi']} Jan Aushadhi, "
                     f"{len(s['emails'])} email(s), {len(s['errors'])} error(s).")
        except Exception as exc:  # never let alerting kill the scheduler
            log.error(f"Alert bot failed: {exc}")


# --------------------------------------------------------------------------- #
# Scheduler setup
# --------------------------------------------------------------------------- #

def main() -> None:
    if not _DB_URL:
        sys.exit("GENUINE_RX_DB_URL is not set — cannot start scheduler.")

    scheduler = BlockingScheduler(timezone="UTC")

    minute, hour, day, month, dow = _CRON.split()
    trigger = CronTrigger(
        minute=minute, hour=hour, day=day, month=month, day_of_week=dow,
        timezone="UTC",
    )

    scheduler.add_job(
        run_daily_pipeline,
        trigger=trigger,
        id="daily_price_scrape",
        name="Genuine RX daily price scrape",
        misfire_grace_time=300,  # tolerate up to 5 min delay
    )

    log.info(f"Scheduler started. Cron: {_CRON} UTC. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
