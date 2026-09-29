"""
alert_keywords.py — Robot Framework keywords for the price-drop alert bot.

Thin wrappers around rpa/alerts/price_alert_bot.py so suites stay readable.
"""
import sys
from pathlib import Path

from robot.api.deco import keyword, library

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from rpa.alerts import price_alert_bot as bot  # noqa: E402


@library(scope="SUITE", auto_keywords=False)
class AlertKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self):
        self._conn = None

    def _db(self):
        if self._conn is None or self._conn.closed:
            self._conn = bot.connect()
            bot.ensure_schema(self._conn)
        return self._conn

    @keyword("Reset Alert Log")
    def reset_alert_log(self) -> None:
        """Forget all previously sent alerts so the bot fires again."""
        bot.reset_alert_log(self._db())

    @keyword("Simulate Price Drop")
    def simulate_price_drop(self, brand_name: str, pct: float = 20) -> dict:
        """Append a new lower price for a tracked medicine (simulated scrape)."""
        return bot.simulate_price_drop(self._db(), brand_name, float(pct))

    @keyword("Run Price Alert Bot")
    def run_price_alert_bot(self, dry_run: bool = False) -> dict:
        """Run detection + email. Returns the summary dict (drops, jan_aushadhi, emails, errors...)."""
        return bot.run_alert_bot(self._db(), dry_run=bool(dry_run))

    @keyword("Read Outbox Email")
    def read_outbox_email(self, path: str) -> str:
        """Return the HTML of an email that the bot saved in rpa/outbox/."""
        return Path(path).read_text(encoding="utf-8")

    @keyword("Close Alert Connection")
    def close_alert_connection(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
