from sqlalchemy.exc import IntegrityError  # for non-PK integrity errors
from app.services.ins_data import transform_rows, insert_eq_data


def main():
    json_data = [
        {"Category": "DII **", "Date": "03-Oct-2025", "Buy Value(₹ Crores)": "13,448.61", "Sell Value (₹ Crores)": "12,920.13", "Net Value (₹ Crores)": "528.48"},
        {"Category": "FII/FPI *", "Date": "03-Oct-2025", "Buy Value(₹ Crores)": "16,496.43", "Sell Value (₹ Crores)": "17,999.55", "Net Value (₹ Crores)": "-1,503.12"},
    ]

    payload = transform_rows(json_data)

    try:
        inserted = insert_eq_data(payload)  # now returns bool
        if inserted:
            print("Inserted: True")
        else:
            print("Insert skipped: primary key already exists for this run_dt.")
    except IntegrityError as err:
        # For integrity errors other than primary key/unique collision
        print("Insert failed due to integrity error:", str(err))


if __name__ == "__main__":
    main()
