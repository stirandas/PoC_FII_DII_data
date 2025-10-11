# app/services/upd_data.py
from __future__ import annotations
from datetime import date, datetime
from contextlib import contextmanager
from sqlalchemy import text
from app.db import get_session
import pytz  # pip install pytz

IST = pytz.timezone("Asia/Kolkata")

@contextmanager
def session_scope():
    s = get_session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()

def touch_timestamp(run_dt: date) -> int:
    with session_scope() as s:
        now_ist = datetime.now(IST)
        s.execute(
            text("UPDATE t_nse_fii_dii_eq_data SET u_ts = :now_ist WHERE run_dt = :d"),
            {"now_ist": now_ist, "d": run_dt},
        )
        return None
