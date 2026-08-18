"""Quick sanity-check — row counts and FK integrity after seed."""
import os
import psycopg

dsn = os.environ["GENUINE_RX_DB_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(dsn) as conn:
    tables = ["salts", "medicines", "medicine_salts", "price_history",
              "users", "tracked_medicines", "caution_list"]
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n} rows")

    orphans = conn.execute("""
        SELECT COUNT(*) FROM medicine_salts ms
        LEFT JOIN medicines m ON ms.medicine_id = m.medicine_id
        WHERE m.medicine_id IS NULL
    """).fetchone()[0]
    print(f"  orphaned medicine_salts: {orphans}")

    jan = conn.execute(
        "SELECT brand_name FROM medicines WHERE is_jan_aushadhi ORDER BY brand_name"
    ).fetchall()
    print(f"  Jan Aushadhi brands: {[r[0] for r in jan]}")

    salt_count = conn.execute("SELECT COUNT(DISTINCT salt_id) FROM medicine_salts").fetchone()[0]
    print(f"  distinct salts referenced in medicine_salts: {salt_count}")
