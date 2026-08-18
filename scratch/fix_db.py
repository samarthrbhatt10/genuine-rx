import psycopg

def fix():
    try:
        conn = psycopg.connect("postgresql://postgres@localhost:5433/postgres", connect_timeout=5)
    except Exception as e:
        print("Connecting without password failed, trying with devpass:", e)
        try:
            conn = psycopg.connect("postgresql://postgres:devpass@localhost:5433/postgres", connect_timeout=5)
        except Exception as e2:
            print("Failed with devpass too:", e2)
            return

    conn.autocommit = True
    conn.execute("ALTER USER postgres WITH PASSWORD 'devpass';")
    print("User postgres password set/verified to devpass.")

    res = conn.execute("SELECT 1 FROM pg_database WHERE datname='genuine_rx'").fetchone()
    if not res:
        conn.execute("CREATE DATABASE genuine_rx;")
        print("Database genuine_rx created.")
    else:
        print("Database genuine_rx already exists.")

if __name__ == "__main__":
    fix()
