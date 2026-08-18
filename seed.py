"""Seed script — expanded realistic Indian pharmacy dataset.

Run after `alembic upgrade head`:

    python seed.py

Requires GENUINE_RX_DB_URL in the environment (or uses devpass@5433 default).
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import psycopg

DB_URL = os.environ.get(
    "GENUINE_RX_DB_URL",
    "postgresql://postgres:devpass@localhost:5433/genuine_rx",
)
dsn = DB_URL.replace("postgresql+psycopg://", "postgresql://")

# ---------------------------------------------------------------------------#
# Salt families — 6 families, realistic Indian pharmacy coverage
# ---------------------------------------------------------------------------#

SALTS = [
    ("Paracetamol",   ["PCM", "Acetaminophen", "Paracetamol Tab",
                       "Paracetamol 500", "Paracetamol 650", "APAP"]),
    ("Ibuprofen",     ["IBU", "Ibuprofen 400", "Brufen Tab",
                       "Advil", "Nurofen"]),
    ("Metformin",     ["Metformin HCl", "Metformin Hydrochloride",
                       "MF 500", "Metformin SR"]),
    ("Atorvastatin",  ["Atorva", "Atorvastatin Calcium",
                       "Atorvastatin 10", "Atorva 10"]),
    ("Pantoprazole",  ["Panto", "PAN 40", "Pan Tab",
                       "Pantoprazole 40", "Pantop"]),
    ("Cetirizine",    ["CTZ", "Cetirizine HCl", "Cetirizine 10",
                       "Cet", "Alerid"]),
]

# ---------------------------------------------------------------------------#
# Medicines — realistic Indian brands incl. Jan Aushadhi generics
# ---------------------------------------------------------------------------#

# (brand_name, form, manufacturer, is_jan_aushadhi, salt_canonical, strength_mg)
MEDICINES = [
    # --- Paracetamol 500 mg ---
    ("Crocin",                    "tablet", "GSK Pharma",            False, "Paracetamol", Decimal("500")),
    ("Calpol",                    "tablet", "GSK Pharma",            False, "Paracetamol", Decimal("500")),
    ("Metacin",                   "tablet", "Pfizer Ltd",            False, "Paracetamol", Decimal("500")),
    ("Pacimol",                   "tablet", "Ipca Laboratories",     False, "Paracetamol", Decimal("500")),
    ("Paracetamol (Jan Aushadhi)","tablet", "PMBI",                  True,  "Paracetamol", Decimal("500")),

    # --- Paracetamol 650 mg (Dolo 650) ---
    ("Dolo 650",                  "tablet", "Micro Labs Ltd",        False, "Paracetamol", Decimal("650")),
    ("Paracetamol 650 (JA)",      "tablet", "PMBI",                  True,  "Paracetamol", Decimal("650")),

    # --- Ibuprofen 400 mg ---
    ("Brufen",                    "tablet", "Abbott India",          False, "Ibuprofen",   Decimal("400")),
    ("Combiflam",                 "tablet", "Sanofi India",          False, "Ibuprofen",   Decimal("400")),
    ("Advil",                     "tablet", "Pfizer India",          False, "Ibuprofen",   Decimal("400")),
    ("Ibuprofen (Jan Aushadhi)",  "tablet", "PMBI",                  True,  "Ibuprofen",   Decimal("400")),

    # --- Metformin 500 mg ---
    ("Glycomet",                  "tablet", "USV Pvt Ltd",           False, "Metformin",   Decimal("500")),
    ("Gluconorm",                 "tablet", "Lupin Ltd",             False, "Metformin",   Decimal("500")),
    ("Walaphage",                 "tablet", "Wallace Pharmaceuticals",False,"Metformin",   Decimal("500")),
    ("Obimet",                    "tablet", "FDC Ltd",               False, "Metformin",   Decimal("500")),
    ("Metformin (Jan Aushadhi)",  "tablet", "PMBI",                  True,  "Metformin",   Decimal("500")),

    # --- Atorvastatin 10 mg ---
    ("Atorva",                    "tablet", "Zydus Cadila",          False, "Atorvastatin",Decimal("10")),
    ("Storvas",                   "tablet", "Sun Pharma",            False, "Atorvastatin",Decimal("10")),
    ("Tonact",                    "tablet", "Lupin Ltd",             False, "Atorvastatin",Decimal("10")),
    ("Lipikind",                  "tablet", "Mankind Pharma",        False, "Atorvastatin",Decimal("10")),
    ("Atorvastatin (Jan Aushadhi)","tablet","PMBI",                  True,  "Atorvastatin",Decimal("10")),

    # --- Pantoprazole 40 mg ---
    ("Pan 40",                    "tablet", "Alkem Laboratories",    False, "Pantoprazole",Decimal("40")),
    ("Pantodac",                  "tablet", "Zydus Cadila",          False, "Pantoprazole",Decimal("40")),
    ("Pantop",                    "tablet", "Aristo Pharmaceuticals",False, "Pantoprazole",Decimal("40")),
    ("Pantoprazole (Jan Aushadhi)","tablet","PMBI",                  True,  "Pantoprazole",Decimal("40")),

    # --- Cetirizine 10 mg ---
    ("Alerid",                    "tablet", "Cipla Ltd",             False, "Cetirizine",  Decimal("10")),
    ("Cetzine",                   "tablet", "GSK Pharma",            False, "Cetirizine",  Decimal("10")),
    ("CTZ",                       "tablet", "Cipla Ltd",             False, "Cetirizine",  Decimal("10")),
    ("Cetirizine (Jan Aushadhi)", "tablet", "PMBI",                  True,  "Cetirizine",  Decimal("10")),
]

# ---------------------------------------------------------------------------#
# Prices — realistic MRP (INR) for 10-tablet strip (as of mid-2026)
# With 4 weeks of price history to make charts meaningful.
# ---------------------------------------------------------------------------#

# Latest price per brand
LATEST_PRICES = {
    # --- Paracetamol 500 mg (10's strip) ---
    # Branded MRPs from 1mg/Netmeds; JA price verified on UMANG portal screenshot
    "Crocin":                      ("primary_pharmacy", Decimal("18.00")),
    "Calpol":                      ("primary_pharmacy", Decimal("16.50")),
    "Metacin":                     ("primary_pharmacy", Decimal("12.00")),
    "Pacimol":                     ("primary_pharmacy", Decimal("11.50")),
    "Paracetamol (Jan Aushadhi)":  ("jan_aushadhi_pdf", Decimal("6.56")),   # UMANG: ₹6.56 / 10 tabs

    # --- Paracetamol 650 mg (15 tabs strip) ---
    "Dolo 650":                    ("primary_pharmacy", Decimal("34.00")),
    "Paracetamol 650 (JA)":        ("jan_aushadhi_pdf", Decimal("14.07")),  # UMANG: ₹14.07 / 15 tabs

    # --- Ibuprofen 400 mg (10's strip) ---
    "Brufen":                      ("primary_pharmacy", Decimal("19.50")),
    "Combiflam":                   ("primary_pharmacy", Decimal("24.00")),
    "Advil":                       ("primary_pharmacy", Decimal("35.00")),
    "Ibuprofen (Jan Aushadhi)":    ("jan_aushadhi_pdf", Decimal("8.25")),   # UMANG: ₹8.25 / 10 tabs

    # --- Metformin 500 mg (10's strip) ---
    "Glycomet":                    ("primary_pharmacy", Decimal("28.50")),
    "Gluconorm":                   ("primary_pharmacy", Decimal("26.00")),
    "Walaphage":                   ("primary_pharmacy", Decimal("22.00")),
    "Obimet":                      ("primary_pharmacy", Decimal("20.00")),
    "Metformin (Jan Aushadhi)":    ("jan_aushadhi_pdf", Decimal("6.74")),   # UMANG: ₹6.74 / 10 tabs

    # --- Atorvastatin 10 mg (10's strip) ---
    "Atorva":                      ("primary_pharmacy", Decimal("72.00")),
    "Storvas":                     ("primary_pharmacy", Decimal("68.00")),
    "Tonact":                      ("primary_pharmacy", Decimal("62.00")),
    "Lipikind":                    ("primary_pharmacy", Decimal("52.00")),
    "Atorvastatin (Jan Aushadhi)": ("jan_aushadhi_pdf", Decimal("10.44")), # UMANG: ₹10.44 / 10 tabs

    # --- Pantoprazole 40 mg (10's strip) ---
    "Pan 40":                      ("primary_pharmacy", Decimal("54.00")),
    "Pantodac":                    ("primary_pharmacy", Decimal("48.00")),
    "Pantop":                      ("primary_pharmacy", Decimal("42.00")),
    "Pantoprazole (Jan Aushadhi)": ("jan_aushadhi_pdf", Decimal("8.82")),  # UMANG: ₹8.82 / 10 tabs

    # --- Cetirizine 10 mg (10's strip) ---
    "Alerid":                      ("primary_pharmacy", Decimal("21.00")),
    "Cetzine":                     ("primary_pharmacy", Decimal("19.00")),
    "CTZ":                         ("primary_pharmacy", Decimal("16.00")),
    "Cetirizine (Jan Aushadhi)":   ("jan_aushadhi_pdf", Decimal("3.65")),  # UMANG: ₹3.65 / 10 tabs
}

# Price history offsets: (days_ago, pct_change_from_latest)
# Simulates realistic price fluctuations over 4 weeks
HISTORY_OFFSETS = [
    (28, Decimal("1.08")),   # 8% higher 4 weeks ago
    (21, Decimal("1.05")),   # 5% higher 3 weeks ago
    (14, Decimal("1.02")),   # 2% higher 2 weeks ago
    (7,  Decimal("1.01")),   # 1% higher 1 week ago
    (0,  Decimal("1.00")),   # current price
]

# Caution list: salt_canonical → reason
CAUTION_SALTS = {
    "Atorvastatin": "Narrow therapeutic index — monitor liver enzymes; avoid grapefruit.",
    "Metformin":    "Contraindicated in severe renal impairment (eGFR < 30) — check creatinine before use.",
}

# Demo users
USERS = [
    ("+919999000001", True),   # user_id 1 — Rahul (main demo user)
    ("+919999000002", True),   # user_id 2 — Priya
]

# Pre-seeded tracked medicines for demo users
# (phone, brand_name, profile_label)
TRACKED = [
    ("+919999000001", "Crocin",   "self"),
    ("+919999000001", "Glycomet", "Papa"),
    ("+919999000001", "Pan 40",   "Amma"),
    ("+919999000002", "Dolo 650", "self"),
    ("+919999000002", "Alerid",   "Husband"),
]


def run_seed(conn: psycopg.Connection) -> None:
    now_utc = datetime.now(timezone.utc)

    # ---- Salts ----
    salt_id_map: dict[str, int] = {}
    for canonical, aliases in SALTS:
        row = conn.execute(
            """
            INSERT INTO salts (canonical_name, aliases)
            VALUES (%s, %s)
            ON CONFLICT (canonical_name) DO UPDATE
                SET aliases = EXCLUDED.aliases
            RETURNING salt_id
            """,
            (canonical, aliases),
        ).fetchone()
        assert row is not None
        salt_id_map[canonical] = row["salt_id"]
        print(f"  salt: {canonical!r} -> id={row['salt_id']}")

    # ---- Medicines ----
    med_id_map: dict[str, int] = {}
    for brand, form, mfr, is_ja, salt_canonical, strength in MEDICINES:
        row = conn.execute(
            """
            INSERT INTO medicines (brand_name, form, manufacturer, is_jan_aushadhi)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING medicine_id
            """,
            (brand, form, mfr, is_ja),
        ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT medicine_id FROM medicines WHERE brand_name = %s", (brand,)
            ).fetchone()
        mid = row["medicine_id"]
        med_id_map[brand] = mid

        conn.execute(
            """
            INSERT INTO medicine_salts (medicine_id, salt_id, strength_mg)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (mid, salt_id_map[salt_canonical], strength),
        )
        print(f"  medicine: {brand!r} -> id={mid}")

    # ---- Price history (4-week series + current) ----
    for brand, (source, latest_price) in LATEST_PRICES.items():
        mid = med_id_map.get(brand)
        if mid is None:
            continue
        for days_ago, multiplier in HISTORY_OFFSETS:
            price = (latest_price * multiplier).quantize(Decimal("0.01"))
            scraped_at = now_utc - timedelta(days=days_ago)
            conn.execute(
                """
                INSERT INTO price_history (medicine_id, source, price, scraped_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (mid, source, price, scraped_at),
            )
        print(f"  price history: {brand!r} -> latest Rs.{latest_price} ({source})")

    # ---- Users ----
    user_id_map: dict[str, int] = {}
    for phone, consent in USERS:
        row = conn.execute(
            """
            INSERT INTO users (phone, consent_whatsapp)
            VALUES (%s, %s)
            ON CONFLICT (phone) DO UPDATE SET consent_whatsapp = EXCLUDED.consent_whatsapp
            RETURNING user_id
            """,
            (phone, consent),
        ).fetchone()
        user_id_map[phone] = row["user_id"]
        print(f"  user: {phone} -> id={row['user_id']}")

    # ---- Tracked medicines ----
    for phone, brand, label in TRACKED:
        uid = user_id_map.get(phone)
        mid = med_id_map.get(brand)
        if uid and mid:
            conn.execute(
                """
                INSERT INTO tracked_medicines (user_id, medicine_id, profile_label)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, medicine_id, profile_label) DO NOTHING
                """,
                (uid, mid, label),
            )
            print(f"  tracked: user {uid} -> {brand!r} ({label})")

    # ---- Caution list ----
    for salt_name, reason in CAUTION_SALTS.items():
        sid = salt_id_map.get(salt_name)
        if sid:
            conn.execute(
                """
                INSERT INTO caution_list (salt_id, reason)
                VALUES (%s, %s)
                ON CONFLICT (salt_id) DO UPDATE SET reason = EXCLUDED.reason
                """,
                (sid, reason),
            )
            print(f"  caution: {salt_name} flagged")

    print("\nDone — seed complete with no FK errors.")


if __name__ == "__main__":
    print(f"Connecting to database…")
    with psycopg.connect(dsn, autocommit=True) as conn:
        from psycopg.rows import dict_row
        conn.row_factory = dict_row
        print("Seeding…")
        run_seed(conn)
