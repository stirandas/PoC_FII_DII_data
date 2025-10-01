# file: scripts/db_conn_check.py
import os, psycopg

DATABASE_URL = os.environ["DATABASE_URL"]  # from .env

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("select count(*) from t_nse_fii_dii_eq_data")
        row = cur.fetchone()
        print({"count": row[0]})
