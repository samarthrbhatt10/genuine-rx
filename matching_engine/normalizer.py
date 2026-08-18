"""
Salt name normalisation and strength unit conversion.

All functions are pure — no I/O, no side effects.

normalise_salt_name()  — for fuzzy comparison only; never mutates stored names.
strength_to_mg()       — canonical unit for storage per 03_DATA_MODEL.md rule 2.
"""
import re
from decimal import Decimal

# Multipliers to convert a value in <unit> to milligrams.
_UNIT_MULTIPLIERS: dict[str, Decimal] = {
    "mg":  Decimal("1"),
    "g":   Decimal("1000"),
    "mcg": Decimal("0.001"),
    "ug":  Decimal("0.001"),
    "µg":  Decimal("0.001"),
    # IU is dimensionless — stored 1:1; callers must not mix IU with mass units.
    "iu":  Decimal("1"),
}

# Salt name suffixes that carry no pharmacological distinction for matching.
_NOISE_SUFFIX_RE = re.compile(
    r"\b("
    r"hydrochloride|hcl|sodium|potassium|calcium|magnesium|zinc|"
    r"acetate|sulfate|sulphate|phosphate|citrate|tartrate|maleate|"
    r"fumarate|besylate|mesylate|succinate|gluconate|chloride|"
    r"bromide|iodide|oxide|nitrate|monohydrate|dihydrate|anhydrous"
    r")\b",
    re.IGNORECASE,
)


def normalize_salt_name(name: str) -> str:
    """Return a noise-stripped, lowercased form for fuzzy comparison.

    This is a *comparison helper* — it must never be used to mutate names
    stored in the database.  Canonical names in `salts.canonical_name` stay
    exactly as authored.

    Examples:
        normalize_salt_name("Metformin Hydrochloride") -> "metformin"
        normalize_salt_name("Paracetamol Tab")         -> "paracetamol tab"
        normalize_salt_name("Atorvastatin Calcium")    -> "atorvastatin"
    """
    name = name.lower().strip()
    name = _NOISE_SUFFIX_RE.sub("", name)
    name = re.sub(r"[^a-z0-9\s]", " ", name)  # replace punctuation with space
    name = re.sub(r"\s+", " ", name).strip()   # collapse whitespace
    return name


def strength_to_mg(value: float | str | Decimal, unit: str) -> Decimal:
    """Convert a strength value + unit string to milligrams (Decimal).

    Raises ValueError for unrecognised units — callers must handle this
    before inserting into medicine_salts.strength_mg.

    Examples:
        strength_to_mg(500, "mg")  -> Decimal("500")
        strength_to_mg(0.5, "g")   -> Decimal("500")
        strength_to_mg(10,  "mcg") -> Decimal("0.010")
    """
    unit_key = unit.lower().strip()
    multiplier = _UNIT_MULTIPLIERS.get(unit_key)
    if multiplier is None:
        raise ValueError(
            f"Unknown strength unit {unit!r}. "
            f"Supported: {sorted(_UNIT_MULTIPLIERS)}"
        )
    return Decimal(str(value)) * multiplier
