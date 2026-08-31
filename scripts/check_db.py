import json
import os
import sys

try:
    import psycopg2
except ImportError:
    print("Install: pip install psycopg2-binary")
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
    cfg = json.load(f)

def pg(section):
    c = cfg[section]["config"]
    return {
        "host": c["host"]["value"],
        "port": int(c["port"]["value"]),
        "dbname": c["db_name"]["value"],
        "user": c["user"]["value"],
        "password": c["password"]["value"],
    }

p = pg("config_store")
conn = psycopg2.connect(connect_timeout=10, **p)
cur = conn.cursor()
cur.execute("SELECT current_database(), current_user")
print("Connected:", cur.fetchone())
cur.execute("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public'")
print("Tables:", cur.fetchone()[0])
conn.close()
