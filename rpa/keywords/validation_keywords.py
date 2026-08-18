"""
validation_keywords.py — Price sanity checking keyword.

``Validate Price Sanity`` compares a newly scraped price against the last
7 entries in price_history.  It is a deterministic, rule-based check —
no ML, no LLM.

Keyword name matches 05_ROBOT_FRAMEWORK_SPEC.md exactly.
"""
import os
import sys
from decimal import Decimal
from pathlib import Path

from robot.api import logger
from robot.api.deco import keyword, library

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Maximum allowed single-step deviation before flagging as implausible.
# If new_price deviates > 300% from median of last 7 AND those 7 were stable
# (std-dev / mean < 10%), the price is considered insane.
_MAX_DEVIATION_PCT = 300.0
_MAX_PRIOR_VOLATILITY_PCT = 10.0


@library(scope="SUITE", auto_keywords=False)
class ValidationKeywords:
    """Keyword library for data-quality validation after a scrape run."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("Validate Price Sanity")
    def validate_price_sanity(self, medicine_id: int, new_price: float) -> bool:
        """Return True if *new_price* is plausible for *medicine_id*.

        Algorithm (rule-based, per spec):
        1. Fetch last 7 price_history rows for this medicine.
        2. If < 2 rows exist, accept unconditionally (not enough history).
        3. Compute median of historical prices.
        4. Compute deviation of new_price from median (%).
        5. If deviation > 300%:
           a. Compute coefficient of variation (std-dev / mean) of the 7 rows.
           b. If CV < 10% (historically stable), FAIL — this spike has no precedent.
           c. If CV >= 10% (historically volatile), WARN but pass.
        6. Otherwise PASS.

        Raises:
            RuntimeError: if GENUINE_RX_DB_URL is not set.
        """
        db_url = os.environ.get("GENUINE_RX_DB_URL")
        if not db_url:
            raise RuntimeError("GENUINE_RX_DB_URL is not set.")

        import psycopg
        dsn = db_url.replace("postgresql+psycopg://", "postgresql://")

        with psycopg.connect(dsn) as conn:
            rows = conn.execute(
                """
                SELECT price FROM price_history
                 WHERE medicine_id = %s
                 ORDER BY scraped_at DESC
                 LIMIT 7
                """,
                (medicine_id,),
            ).fetchall()

        if len(rows) < 2:
            logger.info(
                f"Validate Price Sanity: medicine_id={medicine_id} has < 2 history rows — "
                "accepting unconditionally."
            )
            return True

        prices = [float(r[0]) for r in rows]
        median = _median(prices)

        if median == 0:
            logger.warn(
                f"Validate Price Sanity: median price is 0 for medicine_id={medicine_id} — "
                "accepting (may be a data error, flag separately)."
            )
            return True

        deviation_pct = abs(new_price - median) / median * 100

        if deviation_pct <= _MAX_DEVIATION_PCT:
            logger.info(
                f"Validate Price Sanity: PASS medicine_id={medicine_id} "
                f"new={new_price:.2f} median={median:.2f} dev={deviation_pct:.1f}%"
            )
            return True

        # Deviation is > 300% — check if history was already volatile
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        cv_pct = (std_dev / mean * 100) if mean else 0

        if cv_pct >= _MAX_PRIOR_VOLATILITY_PCT:
            logger.warn(
                f"Validate Price Sanity: WARN medicine_id={medicine_id} "
                f"new={new_price:.2f} dev={deviation_pct:.1f}% but prior CV={cv_pct:.1f}% "
                "(historically volatile — passing with warning)."
            )
            return True

        logger.warn(
            f"Validate Price Sanity: FAIL medicine_id={medicine_id} "
            f"new={new_price:.2f} median={median:.2f} dev={deviation_pct:.1f}% "
            f"prior CV={cv_pct:.1f}% — implausible price spike."
        )
        return False


# --------------------------------------------------------------------------- #
# Private helpers
# --------------------------------------------------------------------------- #

def _median(values: list[float]) -> float:
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    return sorted_vals[mid] if n % 2 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
