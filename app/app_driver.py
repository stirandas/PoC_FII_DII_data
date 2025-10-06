# app/app_driver.py
# This is the main driver script for the application - ST
# Run below command from Repo Root to test
# python -m app.app_driver

import json
from datetime import date
from decimal import Decimal

from app.services.bot_json_msg import bot_json_msg, TelegramSendError
from app.services.br_nse import fetch_json_data
from app.services.ins_data import transform_rows, insert_eq_data
from app.services.upd_data import touch_timestamp


def application_main_driver():  # The application main driver :)
    json_data = fetch_json_data()
    payload = transform_rows(json_data)

    fresh_data_found = insert_eq_data(payload)       #Fresh data found on NSE portal
    if fresh_data_found:
        bot_json_msg(json_data)
    else:
        run_dt = payload["run_dt"]
        touch_timestamp(run_dt)  

if __name__ == "__main__":
    application_main_driver()
