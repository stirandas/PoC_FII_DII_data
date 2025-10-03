# tests/test_table_sync.py

# Ensure project root (parent of "tests") is on sys.path when running directly
import sys
import pathlib
root = pathlib.Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))  # make "app" importable when running directly [web:129][web:132]

import os
from dotenv import load_dotenv
import psycopg

from app.services.table_sync import upsert_fii_dii_data  # function under test [web:129][web:132]

# Load environment variables from .env (project root)
load_dotenv()  # populates os.environ for local runs and pytest [web:76][web:77]
DATABASE_URL = os.getenv("DATABASE_URL")
assert DATABASE_URL, "DATABASE_URL must be set in .env or environment"  # fail fast if missing [web:77]

def test_upsert_single_day(capsys=None):
    # Sample payload in the module's shape
    data = [
        {
            "Category": "DII **",
            "Date": "01-Oct-2025",
            "Buy Value(₹ Crores)": "14,383.93",
            "Sell Value (₹ Crores)": "11,521.86",
            "Net Value (₹ Crores)": "2,862.07",
        },
        {
            "Category": "FII/FPI *",
            "Date": "01-Oct-2025",
            "Buy Value(₹ Crores)": "11,878.50",
            "Sell Value (₹ Crores)": "13,423.58",
            "Net Value (₹ Crores)": "-1,545.08",
        },
    ]

    # Use autocommit so changes persist immediately without explicit commit [web:180][web:88]
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        count, actions = upsert_fii_dii_data(data, conn)  # function should print "<action> row for run_dt=..." [web:12]

    # Validate results
    assert count == 1
    assert len(actions) == 1
    run_dt, action = actions[0]
    assert action in {"inserted", "updated"}

    # Optionally verify printed message
    if capsys is not None:
        out = capsys.readouterr().out
        assert "row for run_dt=" in out
