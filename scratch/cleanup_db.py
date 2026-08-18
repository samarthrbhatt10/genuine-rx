"""Clean database and reseed properly."""
import psycopg
from psycopg.rows import dict_row

dsn = "postgresql://postgres:devpass@localhost:5433/genuine_rx"

with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
    # Inspect schema
    cols = conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='price_history' ORDER BY ordinal_position"
    ).fetchall()
    print("price_history columns:", [c["column_name"] for c in cols])

    pk_col = cols[0]["column_name"]   # whatever the PK is called
    print(f"PK column: {pk_col}")

    # Remove duplicates (keep one row per medicine+day+source)
    conn.execute(f"""
        DELETE FROM price_history
        WHERE {pk_col} NOT IN (
            SELECT MIN({pk_col})
            FROM price_history
            GROUP BY medicine_id, source, scraped_at::date
        )
    """)
    print("Removed duplicate price_history rows")

    # Remove old medicines (ids <= 131 from previous seed runs)
    conn.execute("DELETE FROM tracked_medicines WHERE medicine_id <= 131")
    conn.execute("DELETE FROM medicine_salts WHERE medicine_id <= 131")
    conn.execute("DELETE FROM price_history WHERE medicine_id <= 131")
    conn.execute("DELETE FROM medicines WHERE medicine_id <= 131")
    print("Removed old medicines 1-15")

    # Re-seed tracked medicines for fresh users
    # User 1 = Rahul, User 3 = Priya
    seeds = [
        (1, "Crocin",   "self"),
        (1, "Glycomet", "Papa"),
        (1, "Pan 40",   "Amma"),
        (3, "Dolo 650", "self"),
        (3, "Alerid",   "Husband"),
    ]
    for uid, brand, label in seeds:
        row = conn.execute("SELECT medicine_id FROM medicines WHERE brand_name = %s", (brand,)).fetchone()
        if row:
            conn.execute(
                "INSERT INTO tracked_medicines (user_id, medicine_id, profile_label) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (uid, row["medicine_id"], label)
            )
            print(f"  tracked: user {uid} -> {brand} ({label})")
        else:
            print(f"  WARNING: {brand} not found")

    # Final counts
    meds    = conn.execute("SELECT count(*) as c FROM medicines").fetchone()["c"]
    hist    = conn.execute("SELECT count(*) as c FROM price_history").fetchone()["c"]
    tracked = conn.execute("SELECT count(*) as c FROM tracked_medicines").fetchone()["c"]
    print(f"\nFinal: {meds} medicines | {hist} price_history rows | {tracked} tracked")
