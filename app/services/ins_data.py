# app/services/ins_data.py
from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Any, TypedDict
from contextlib import contextmanager

import pytz
from sqlalchemy.exc import IntegrityError

from app.db import get_session
from app.models import TNseFiiDiiEqData

# Define IST timezone
IST = pytz.timezone("Asia/Kolkata")


class EqPayload(TypedDict):
    run_dt: date
    dii_buy: Decimal | None
    dii_sell: Decimal | None
    dii_net: Decimal | None
    fii_buy: Decimal | None
    fii_sell: Decimal | None
    fii_net: Decimal | None


def transform_rows(rows: list[dict[str, Any]]) -> EqPayload:
    dii_row = next((r for r in rows if r.get("Category", "").strip().startswith("DII")), None)
    fii_row = next((r for r in rows if r.get("Category", "").strip().startswith("FII")), None)
    if not dii_row or not fii_row:
        raise ValueError("Expected both DII and FII/FPI rows in payload")

    def _to_date(d: str) -> date:
        return datetime.strptime(d.strip(), "%d-%b-%Y").date()

    def _to_decimal(s: str | None) -> Decimal | None:
        if s is None:
            return None
        s = s.strip().replace(",", "")
        return None if s == "" else Decimal(s)

    run_dt = _to_date(dii_row["Date"])
    return {
        "run_dt": run_dt,
        "dii_buy": _to_decimal(dii_row.get("Buy Value(₹ Crores)")),
        "dii_sell": _to_decimal(dii_row.get("Sell Value (₹ Crores)")),
        "dii_net": _to_decimal(dii_row.get("Net Value (₹ Crores)")),
        "fii_buy": _to_decimal(fii_row.get("Buy Value(₹ Crores)")),
        "fii_sell": _to_decimal(fii_row.get("Sell Value (₹ Crores)")),
        "fii_net": _to_decimal(fii_row.get("Net Value (₹ Crores)")),
    }


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


def insert_eq_data(payload: EqPayload) -> bool:
    """Attempt to insert; return True on success.
    On any primary key/unique-like collision, return False and exit gracefully.
    """

    def _net(buy: Decimal | None, sell: Decimal | None) -> Decimal | None:
        if buy is None or sell is None:
            return None
        return (buy - sell).quantize(Decimal("0.01"))

    dii_net = payload["dii_net"] if payload["dii_net"] is not None else _net(payload["dii_buy"], payload["dii_sell"])
    fii_net = payload["fii_net"] if payload["fii_net"] is not None else _net(payload["fii_buy"], payload["fii_sell"])

    # Generate IST timestamp for insertion
    i_ts_ist = datetime.now(IST)

    with session_scope() as s:
        try:
            row = TNseFiiDiiEqData(
                run_dt=payload["run_dt"],
                dii_buy=payload["dii_buy"],
                dii_sell=payload["dii_sell"],
                dii_net=dii_net,
                fii_buy=payload["fii_buy"],
                fii_sell=payload["fii_sell"],
                fii_net=fii_net,
                i_ts=i_ts_ist,  # New IST timestamp column
            )
            s.add(row)
            s.flush()
            return True
        except IntegrityError:
            s.rollback()
            return False
