import psycopg
from psycopg.rows import dict_row

dsn = "postgresql://postgres:devpass@localhost:5433/genuine_rx"
with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
    rows = conn.execute(
        "SELECT tm.user_id, m.brand_name, tm.profile_label "
        "FROM tracked_medicines tm JOIN medicines m USING(medicine_id) ORDER BY user_id"
    ).fetchall()
    print("=== Tracked medicines ===")
    for r in rows:
        print(f"  user {r['user_id']} -> {r['brand_name']} ({r['profile_label']})")

    # Verify Priya's dashboard
    priya = conn.execute(
        "SELECT m.brand_name, m.latest_price FROM ("
        "  SELECT tm.medicine_id, (SELECT price FROM price_history WHERE medicine_id=tm.medicine_id ORDER BY scraped_at DESC LIMIT 1) as latest_price "
        "  FROM tracked_medicines tm WHERE user_id=3) m2 JOIN medicines m ON m.medicine_id=m2.medicine_id"
    ).fetchall()
    print("\n=== Priya's watchlist ===")
    for r in priya:
        print(f"  {r['brand_name']}: Rs.{r['latest_price']}")
