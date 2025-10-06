# app/main.py
#from fastapi import FastAPI  # Web framework entrypoint. [web:359]
from app.services.br_nse import fetch_json_data  
import json

#app = FastAPI()  # Create the ASGI app. [web:359]

def main_script():
    json_data = fetch_json_data()  # Call the function to fetch data
    print(json.dumps(json_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main_script()


# app/main.py
from datetime import date
from decimal import Decimal

from app.services.insert_eq_data import insert_eq_data
from app.services.update_eq_data import update_eq_data

def main():
    # insert
    insert_eq_data(
        run_dt=date(2025, 10, 3),
        dii_buy=Decimal("13448.61"),
        dii_sell=Decimal("12920.13"),
        fii_buy=Decimal("16496.43"),
        fii_sell=Decimal("17999.55"),
    )

    # update
    update_eq_data(
        run_dt=date(2025, 10, 3),
        dii_buy=Decimal("13450.00"),
    )

if __name__ == "__main__":
    main()
