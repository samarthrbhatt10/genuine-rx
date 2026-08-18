"""
Data types for the matching engine.

All types are pure dataclasses — no SQLAlchemy, no network, no I/O.
The API layer is responsible for fetching rows from Postgres/Redis and
hydrating these objects before calling find_substitutes().
"""
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class SaltEntry:
    """One row from the `salts` table, with aliases normalised to lowercase."""
    salt_id: int
    canonical_name: str
    aliases: frozenset  # frozenset[str] — all lowercase for O(1) lookup


@dataclass(frozen=True)
class SaltRequirement:
    """One (salt, strength) pair in a medicine's composition.

    Frozen + hashable so it can live in a frozenset for order-independent
    comparison of combination-drug compositions.
    """
    salt_id: int
    strength_mg: Decimal


@dataclass
class MedicineEntry:
    """One row from `medicines` joined with its `medicine_salts` rows."""
    medicine_id: int
    brand_name: str
    form: str                   # tablet | syrup | capsule | injection
    manufacturer: str | None
    is_jan_aushadhi: bool
    salts: frozenset            # frozenset[SaltRequirement] — order-independent


@dataclass
class PriceEntry:
    """Most-recent row from `price_history` for one medicine."""
    medicine_id: int
    source: str                 # 'primary_pharmacy' | 'jan_aushadhi_pdf'
    price: Decimal


@dataclass
class SubstituteResult:
    """One ranked entry in the substitute list returned to the caller."""
    medicine_id: int
    brand_name: str
    form: str
    manufacturer: str | None
    is_jan_aushadhi: bool
    price: Decimal
    source: str
    caution_flag: bool
    caution_reason: str | None
    savings_pct: float | None   # vs. most expensive in the result set
