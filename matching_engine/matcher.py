"""
Core matching pipeline — pure functions, no I/O.

find_substitutes() is the single entry point called by both the FastAPI
layer and Robot Framework keyword library.  It never hits the network or
the database directly; the caller hydrates the data and passes it in.
"""
from decimal import Decimal

from .normalizer import normalize_salt_name
from .ranker import rank_substitutes
from .resolver import resolve_alias
from .types import (
    MedicineEntry,
    PriceEntry,
    SaltEntry,
    SaltRequirement,
    SubstituteResult,
)


def _resolve_query_salts(
    query_salts: list[tuple[str, Decimal]],
    salt_table: list[SaltEntry],
) -> frozenset[SaltRequirement]:
    """Resolve raw (name, strength_mg) pairs -> frozenset[SaltRequirement].

    Raises ValueError listing every unresolvable name.  Never silently
    drops a salt — an incomplete composition must not match anything.
    """
    requirements: list[SaltRequirement] = []
    unresolved: list[str] = []

    for raw_name, strength_mg in query_salts:
        entry = resolve_alias(raw_name, salt_table)
        if entry is None:
            unresolved.append(raw_name)
        else:
            requirements.append(SaltRequirement(
                salt_id=entry.salt_id,
                strength_mg=strength_mg,
            ))

    if unresolved:
        raise ValueError(
            f"Cannot resolve salt name(s): {unresolved}. "
            "Add the name to salts.aliases or check the spelling."
        )

    return frozenset(requirements)


def find_substitutes(
    query_salts: list[tuple[str, Decimal]],
    salt_table: list[SaltEntry],
    medicine_table: list[MedicineEntry],
    price_table: list[PriceEntry],
    caution_salt_ids: dict[int, str],   # salt_id -> reason string
) -> list[SubstituteResult]:
    """Find, rank, and annotate all medicines sharing the exact same salt composition.

    Matching rules (from 06_FEATURES.md Module B and Module E):
    - Exact salt-set match — same salts, same strengths, same count.
    - Order-independent — composition is compared as frozensets.
    - No fuzzy-salt fallback, ever (Module E rule).
    - Caution list checked on every lookup, not as an afterthought.
    - Ranking: is_jan_aushadhi DESC, price ASC (fixed, per API contract).

    Args:
        query_salts:      List of (raw_salt_name, strength_mg) tuples.
                          Names may be aliases — resolve_alias handles them.
        salt_table:       All SaltEntry rows from the `salts` table.
        medicine_table:   All MedicineEntry rows (each with its salt frozenset).
        price_table:      Latest PriceEntry per medicine.  If multiple rows
                          exist for one medicine, the FIRST one in the list
                          wins — callers should pre-sort by scraped_at DESC.
        caution_salt_ids: Mapping of salt_id -> caution reason from
                          `caution_list` table.

    Returns:
        Ranked list of SubstituteResult.  Empty list = no substitutes found.
        savings_pct on each result is relative to the most expensive entry
        in the set (0.0 for the most expensive itself).

    Raises:
        ValueError: if any salt name in query_salts cannot be resolved.
    """
    query_key = _resolve_query_salts(query_salts, salt_table)

    # Index: medicine_id -> first (most recent) price entry
    price_index: dict[int, PriceEntry] = {}
    for p in price_table:
        if p.medicine_id not in price_index:
            price_index[p.medicine_id] = p

    results: list[SubstituteResult] = []
    for med in medicine_table:
        # Exact-match only — frozenset equality handles order independence
        if med.salts != query_key:
            continue

        price_entry = price_index.get(med.medicine_id)
        if price_entry is None:
            # RPA has not yet scraped a price for this medicine — skip.
            continue

        # Caution check: flag if ANY salt in this medicine is on caution list
        caution_reason: str | None = None
        for req in med.salts:
            if req.salt_id in caution_salt_ids:
                caution_reason = caution_salt_ids[req.salt_id]
                break

        results.append(SubstituteResult(
            medicine_id=med.medicine_id,
            brand_name=med.brand_name,
            form=med.form,
            manufacturer=med.manufacturer,
            is_jan_aushadhi=med.is_jan_aushadhi,
            price=price_entry.price,
            source=price_entry.source,
            caution_flag=caution_reason is not None,
            caution_reason=caution_reason,
            savings_pct=None,
        ))

    ranked = rank_substitutes(results)

    # Compute savings_pct relative to most expensive in this result set
    if ranked:
        max_price = max(r.price for r in ranked)
        for r in ranked:
            r.savings_pct = (
                float((max_price - r.price) / max_price * 100)
                if max_price > 0
                else 0.0
            )

    return ranked
