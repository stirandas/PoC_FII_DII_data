# app/tests/test_insert.py
from sqlalchemy.exc import IntegrityError  # for PK violations [web:437]
from app.services.ins_data import transform_rows, insert_eq_data

def main():
    json_data = [
        {"Category": "DII **", "Date": "03-Oct-2025", "Buy Value(₹ Crores)": "13,448.61", "Sell Value (₹ Crores)": "12,920.13", "Net Value (₹ Crores)": "528.48"},
        {"Category": "FII/FPI *", "Date": "03-Oct-2025", "Buy Value(₹ Crores)": "16,496.43", "Sell Value (₹ Crores)": "17,999.55", "Net Value (₹ Crores)": "-1,503.12"},
    ]

    payload = transform_rows(json_data)

    try:
        row = insert_eq_data(payload)
        print("Inserted:", row.run_dt, row.dii_buy, row.dii_sell, row.dii_net, row.fii_buy, row.fii_sell, row.fii_net)
    except IntegrityError as err:
        # Short, clear message without a long traceback
        print("Insert skipped: primary key already exists for this run_dt.", str(err.orig))  # concise [web:433][web:437])

if __name__ == "__main__":
    main()
