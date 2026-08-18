"""
matching_engine — pure Python, no I/O.

Public surface (everything else is an implementation detail):

    find_substitutes(query_salts, salt_table, medicine_table,
                     price_table, caution_salt_ids)
        -> list[SubstituteResult]

    resolve_alias(raw_name, salt_table) -> SaltEntry | None
    normalize_salt_name(name)           -> str
    strength_to_mg(value, unit)         -> Decimal

    Types: SaltEntry, SaltRequirement, MedicineEntry, PriceEntry, SubstituteResult
"""
from .matcher import find_substitutes
from .normalizer import normalize_salt_name, strength_to_mg
from .resolver import resolve_alias
from .types import (
    MedicineEntry,
    PriceEntry,
    SaltEntry,
    SaltRequirement,
    SubstituteResult,
)

__all__ = [
    "find_substitutes",
    "resolve_alias",
    "normalize_salt_name",
    "strength_to_mg",
    "SaltEntry",
    "SaltRequirement",
    "MedicineEntry",
    "PriceEntry",
    "SubstituteResult",
]
