"""
parsing_keywords.py — Salt string parsing and PDF parsing keywords.

``Normalize Salt String`` is a pure function (no I/O at call time).
``Parse Jan Aushadhi PDF`` uses RPA.PDF (requires the 3.11 venv).
``Match Salt To Substitutes`` is a thin wrapper around matching_engine —
    the matching logic is NOT reimplemented here.

Keyword names match 05_ROBOT_FRAMEWORK_SPEC.md exactly.
"""
import os
import re
import sys
from decimal import Decimal
from pathlib import Path

from robot.api import logger
from robot.api.deco import keyword, library

# Add repo root to path so matching_engine can always be imported,
# regardless of where `robot` is invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from matching_engine.normalizer import normalize_salt_name, strength_to_mg
from matching_engine.resolver import resolve_alias
from matching_engine.types import SaltEntry


# Regex: matches "<name> <value><unit>" e.g. "Paracetamol 500mg", "Metformin HCl 500 mg"
_SALT_STRENGTH_RE = re.compile(
    r"([A-Za-z][A-Za-z0-9\s\-\.]+?)"   # drug name (non-greedy)
    r"\s+"
    r"(\d+(?:\.\d+)?)"                   # numeric value
    r"\s*"
    r"(mg|g|mcg|ug|µg|iu)",             # unit
    re.IGNORECASE,
)

# Separator between salts in a combination string, e.g. "Salt A 500mg + Salt B 5mg"
_COMBO_SEP_RE = re.compile(r"\s*[+/]\s*")


@library(scope="SUITE", auto_keywords=False)
class ParsingKeywords:
    """Parsing keywords for salt strings and Jan Aushadhi PDFs.

    Salt table is loaded once at initialization from the DB if
    GENUINE_RX_DB_URL is set; otherwise an empty table is used
    (alias resolution won't fire, but strength parsing still works).
    The ``Load Salt Aliases`` keyword can refresh the table at any time.
    """

    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self, db_url: str | None = None):
        self._salt_table: list[SaltEntry] = []
        _url = db_url or os.environ.get("GENUINE_RX_DB_URL")
        if _url:
            try:
                self._salt_table = _load_salt_table(_url)
                logger.info(f"ParsingKeywords: loaded {len(self._salt_table)} salts from DB.")
            except Exception as exc:
                logger.warn(f"ParsingKeywords: could not load salt table ({exc}). "
                            "Alias resolution will be skipped.")

    # ------------------------------------------------------------------ #
    # Keywords
    # ------------------------------------------------------------------ #

    @keyword("Load Salt Aliases")
    def load_salt_aliases(self, db_url: str | None = None) -> None:
        """(Re)load the alias table from the database.

        Call this in Suite Setup if the library was initialised without a
        DB URL, or after a seed run that added new aliases.
        """
        url = db_url or os.environ.get("GENUINE_RX_DB_URL")
        if not url:
            raise ValueError(
                "No DB URL provided and GENUINE_RX_DB_URL is not set."
            )
        self._salt_table = _load_salt_table(url)
        logger.info(f"Loaded {len(self._salt_table)} salts.")

    @keyword("Inject Salt Aliases For Testing")
    def inject_salt_aliases_for_testing(self, entries: list[SaltEntry]) -> None:
        """Inject a pre-built salt table for unit/regression testing.

        Avoids any DB connection — use this in regression.robot Suite Setup.
        """
        self._salt_table = entries
        logger.info(f"Injected {len(entries)} test salt aliases.")

    @keyword("Normalize Salt String")
    def normalize_salt_string(self, raw: str) -> list[tuple[str, float]]:
        """Parse a raw salt string into a list of (canonical_name, strength_mg) tuples.

        Pure function at call time — no I/O during execution.
        Alias table is pre-loaded at library init or via ``Load Salt Aliases``.

        Examples:
            "Paracetamol 500mg"               -> [("Paracetamol", 500.0)]
            "Metformin HCl 500 mg"            -> [("Metformin", 500.0)]
            "PCM 500mg"                        -> [("Paracetamol", 500.0)]
            "Metformin 500mg + Glibenclamide 5mg" -> [("Metformin", 500.0), ("Glibenclamide", 5.0)]

        Returns:
            list of (resolved_canonical_name, strength_in_mg) tuples.
            Unresolvable names are returned normalized-as-is (not raised)
            because the caller (e.g. regression suite) decides how to
            handle unknown salts.
        """
        segments = _COMBO_SEP_RE.split(raw.strip())
        results: list[tuple[str, float]] = []

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            match = _SALT_STRENGTH_RE.search(segment)
            if match is None:
                logger.warn(
                    f"Normalize Salt String: could not parse segment {segment!r} — skipping."
                )
                continue

            raw_name = match.group(1).strip()
            raw_value = match.group(2)
            raw_unit = match.group(3)

            try:
                strength_mg = strength_to_mg(raw_value, raw_unit)
            except ValueError as exc:
                logger.warn(f"Normalize Salt String: {exc} — skipping segment.")
                continue

            # Attempt alias resolution; fall back to normalize_salt_name form
            entry = resolve_alias(raw_name, self._salt_table)
            canonical = entry.canonical_name if entry else normalize_salt_name(raw_name).title()

            results.append((canonical, float(strength_mg)))

        return results

    @keyword("Match Salt To Substitutes")
    def match_salt_to_substitutes(self, medicine_id: int) -> list[dict]:
        """Return ranked substitutes for the medicine identified by *medicine_id*.

        Thin RF wrapper around matching_engine.find_substitutes — the
        matching logic is NOT reimplemented here (per spec).  All data is
        fetched from the database and passed into the pure function.
        """
        db_url = os.environ.get("GENUINE_RX_DB_URL")
        if not db_url:
            raise ValueError("GENUINE_RX_DB_URL is not set.")

        from matching_engine import find_substitutes
        from matching_engine.types import (
            MedicineEntry,
            PriceEntry,
            SaltRequirement,
        )

        import psycopg
        dsn = db_url.replace("postgresql+psycopg://", "postgresql://")

        with psycopg.connect(dsn) as conn:
            # Fetch this medicine's salt composition
            rows = conn.execute(
                "SELECT salt_id, strength_mg FROM medicine_salts WHERE medicine_id = %s",
                (medicine_id,),
            ).fetchall()
            if not rows:
                logger.warn(f"No salt composition found for medicine_id={medicine_id}.")
                return []

            query_salts_resolved = frozenset(
                SaltRequirement(salt_id=r[0], strength_mg=Decimal(str(r[1])))
                for r in rows
            )

            # Load full tables needed by matching_engine
            salt_rows = conn.execute(
                "SELECT salt_id, canonical_name, aliases FROM salts"
            ).fetchall()
            salt_table = [
                SaltEntry(r[0], r[1], frozenset(a.lower() for a in (r[2] or [])))
                for r in salt_rows
            ]

            med_rows = conn.execute("""
                SELECT m.medicine_id, m.brand_name, m.form, m.manufacturer,
                       m.is_jan_aushadhi,
                       array_agg(ms.salt_id)     AS salt_ids,
                       array_agg(ms.strength_mg) AS strengths
                  FROM medicines m
                  JOIN medicine_salts ms USING (medicine_id)
                 GROUP BY m.medicine_id
            """).fetchall()
            medicine_table = [
                MedicineEntry(
                    r[0], r[1], r[2], r[3], r[4],
                    frozenset(
                        SaltRequirement(sid, Decimal(str(smg)))
                        for sid, smg in zip(r[5], r[6])
                    ),
                )
                for r in med_rows
            ]

            price_rows = conn.execute("""
                SELECT DISTINCT ON (medicine_id)
                       medicine_id, source, price
                  FROM price_history
                 ORDER BY medicine_id, scraped_at DESC
            """).fetchall()
            price_table = [
                PriceEntry(r[0], r[1], Decimal(str(r[2]))) for r in price_rows
            ]

            caution_rows = conn.execute(
                "SELECT salt_id, reason FROM caution_list"
            ).fetchall()
            caution_salt_ids = {r[0]: r[1] for r in caution_rows}

        # Build query_salts from the medicine's own composition
        # (name-based lookup for the medicine's salts)
        salt_id_to_name = {s.salt_id: s.canonical_name for s in salt_table}
        query_salts = [
            (salt_id_to_name[req.salt_id], req.strength_mg)
            for req in query_salts_resolved
            if req.salt_id in salt_id_to_name
        ]

        results = find_substitutes(
            query_salts, salt_table, medicine_table, price_table, caution_salt_ids
        )
        return [
            {
                "medicine_id":    r.medicine_id,
                "brand_name":     r.brand_name,
                "form":           r.form,
                "manufacturer":   r.manufacturer,
                "is_jan_aushadhi": r.is_jan_aushadhi,
                "price":          float(r.price),
                "source":         r.source,
                "caution_flag":   r.caution_flag,
                "caution_reason": r.caution_reason,
                "savings_pct":    r.savings_pct,
            }
            for r in results
        ]

    @keyword("Parse Jan Aushadhi PDF")
    def parse_jan_aushadhi_pdf(self, pdf_path: str) -> list[dict]:
        """Parse a Jan Aushadhi price-list PDF and return structured rows.

        Uses RPA.PDF (rpaframework) — requires the Python 3.11 venv.
        Returns rows of {drug_name, salt_text, unit_price}.

        Per 06_FEATURES.md Module C: re-parse only when a new list is
        published, not on every daily run.
        """
        try:
            from RPA.PDF import PDF  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "rpaframework is not installed. "
                "Install it in the Python 3.11 venv: pip install -r requirements-rpa.txt"
            ) from exc

        pdf = PDF()
        pages = pdf.get_text_from_pdf(pdf_path)
        full_text = "\n".join(pages.values())

        # Jan Aushadhi PDF format (approximate):
        # Each row: <serial>  <drug_name>  <salt_text>  <unit_price>
        rows: list[dict] = []
        # Pattern: line starting with a number, drug name, salt, price
        line_re = re.compile(
            r"^\s*\d+\s+"                   # serial number
            r"(.+?)\s{2,}"                   # drug_name (2+ spaces as separator)
            r"(.+?)\s{2,}"                   # salt_text (2+ spaces)
            r"(\d+(?:\.\d{1,2})?)\s*$",      # unit_price
            re.MULTILINE,
        )
        for m in line_re.finditer(full_text):
            rows.append({
                "drug_name":  m.group(1).strip(),
                "salt_text":  m.group(2).strip(),
                "unit_price": float(m.group(3)),
            })

        logger.info(f"Parsed {len(rows)} rows from Jan Aushadhi PDF: {pdf_path}")
        return rows


# --------------------------------------------------------------------------- #
# Private helpers
# --------------------------------------------------------------------------- #

def _load_salt_table(db_url: str) -> list[SaltEntry]:
    """Load all rows from `salts` into SaltEntry objects."""
    import psycopg
    dsn = db_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT salt_id, canonical_name, aliases FROM salts"
        ).fetchall()
    return [
        SaltEntry(
            salt_id=r[0],
            canonical_name=r[1],
            aliases=frozenset(a.lower() for a in (r[2] or [])),
        )
        for r in rows
    ]
