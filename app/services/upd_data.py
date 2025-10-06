# app/services/upd_data.py
from __future__ import annotations
from datetime import date
from contextlib import contextmanager
from sqlalchemy import text
from app.db import get_session

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
        res = s.execute(
            text("UPDATE t_nse_fii_dii_eq_data SET iu_ts = now() WHERE run_dt = :d"),
            {"d": run_dt},
        )
        #return res.rowcount   #Only for testing
        return None 