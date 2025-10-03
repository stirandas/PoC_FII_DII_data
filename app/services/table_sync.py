from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
import psycopg  # psycopg3

# Helpers
_INR_NUM_RE = re.compile(r"[^\d\-\.,]")  # keep digits, sign, dot, comma

def _to_decimal_inr(s: str) -> Decimal:
    """
    Convert Indian-formatted currency string to Decimal.cd services
    Examples: '14,383.93' -> Decimal('14383.93'), '-1,545.08' -> Decimal('-1545.08')
    """
    if s is None:
        return Decimal("0")
    # Remove currency symbols/words and spaces
    cleaned = _INR_NUM_RE.sub("", s).strip()
    # Remove grouping commas; keep the last dot as decimal separator
    cleaned = cleaned.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"Cannot parse numeric value: {s!r}")  # fail loud for data quality

def _parse_date(d: str) -> datetime.date:
    # Input like '01-Oct-2025'
    try:
        return datetime.strptime(d.strip(), "%d-%b-%Y").date()
    except ValueError:
        # Allow alternative '01-October-2025' if ever encountered
        return datetime.strptime(d.strip(), "%d-%B-%Y").date()

def upsert_fii_dii_data(records: list[dict], conn: "psycopg.Connection") -> int:
    """
    Insert/Update FII/DII daily equity cash data into t_nse_fii_dii_eq_data.

    records: list of dicts as provided by the module.
    conn: open psycopg3 connection with autocommit off (recommended).
    Returns number of rows upserted (1 per distinct date).
    """
    # Normalize payload into a date-indexed dict with separate maps for DII and FII
    per_date = {}
    for rec in records:
        cat_raw = (rec.get("Category") or "").strip()
        # Normalize category keys
        if cat_raw.upper().startswith("DII"):
            cat = "DII"
        elif cat_raw.upper().startswith("FII"):
            cat = "FII"
        else:
            raise ValueError(f"Unknown Category: {cat_raw}")

        run_dt = _parse_date(rec["Date"])
        buy = _to_decimal_inr(rec.get("Buy Value(₹ Crores)") or rec.get("Buy Value (₹ Crores)") or "0")
        sell = _to_decimal_inr(rec.get("Sell Value (₹ Crores)") or rec.get("Sell Value(₹ Crores)") or "0")
        net = _to_decimal_inr(rec.get("Net Value (₹ Crores)") or "0")

        per_date.setdefault(run_dt, {"DII": {"buy": Decimal("0"), "sell": Decimal("0"), "net": Decimal("0")},
                                     "FII": {"buy": Decimal("0"), "sell": Decimal("0"), "net": Decimal("0")}})
        per_date[run_dt][cat] = {"buy": buy, "sell": sell, "net": net}

    upsert_sql = """
        INSERT INTO t_nse_fii_dii_eq_data
            (run_dt, dii_buy, dii_sell, dii_net, fii_buy, fii_sell, fii_net)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (run_dt) DO UPDATE SET
            dii_buy = EXCLUDED.dii_buy,
            dii_sell = EXCLUDED.dii_sell,
            dii_net = EXCLUDED.dii_net,
            fii_buy = EXCLUDED.fii_buy,
            fii_sell = EXCLUDED.fii_sell,
            fii_net = EXCLUDED.fii_net;
    """  # Uses EXCLUDED for concise, safe UPSERT [web:2][web:4].

    rows = []
    for run_dt, buckets in per_date.items():
        dii = buckets["DII"]
        fii = buckets["FII"]
        rows.append((
            run_dt,
            dii["buy"], dii["sell"], dii["net"],
            fii["buy"], fii["sell"], fii["net"],
        ))

    # Execute in a single transaction with executemany for efficiency
    with conn.cursor() as cur:
        cur.executemany(upsert_sql, rows)  # parameterized, safe against injection [web:12][web:15][web:9]
    conn.commit()
    return len(rows)
