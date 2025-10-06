# app/app_driver.py
# This is the main driver script for the application - ST

#from fastapi import FastAPI  # Web framework entrypoint. [web:359]
import json

from datetime import date
from decimal import Decimal

from app.services.br_nse import fetch_json_data  
from app.services.ins_data import transform_rows, insert_eq_data
from app.services.upd_data import touch_timestamp
from datetime import date

#app = FastAPI()  # Create the ASGI app. [web:359]

def app_dr():
    
    json_data = fetch_json_data()

    print(json.dumps(json_data, indent=2, ensure_ascii=False))

    payload = transform_rows(json_data)
    try:
        row = insert_eq_data(payload)
        print("Inserted:", row.run_dt, row.dii_buy, row.dii_sell, row.dii_net, row.fii_buy, row.fii_sell, row.fii_net)
    except IntegrityError as err:
        # Short, clear message without a long traceback
        print("Insert skipped: primary key already exists for this run_dt.", str(err.orig))  # concise [web:433][web:437])


    # update
    update_eq_data(
        run_dt=date(2025, 10, 3),
        dii_buy=Decimal("13450.00"),
    )

if __name__ == "__main__":
    main()
