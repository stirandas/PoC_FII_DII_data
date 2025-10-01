# app/main.py
from fastapi import FastAPI  # Web framework entrypoint. [web:359]
from app.services.fetch_json_data import get_fiidii_trade_json, NseClient  # Import service. [web:347]

app = FastAPI()  # Create the ASGI app. [web:359]

# Simple endpoint that runs a one-shot fetch each time it's called.
@app.get("/fiidii")
def fiidii_snapshot():
    return get_fiidii_trade_json()  # Quick path for manual checks and dashboards. [web:347]

# Reusable client if multiple endpoints need NSE data during the app lifetime.
client = NseClient()  # Construct once at startup. [web:347]
client.boot_session()  # Warm cookies once, reuse for better stability. [web:336][web:335]

@app.get("/fiidii/reuse")
def fiidii_snapshot_reuse():
    return client.get_fiidii_trade()  # Avoids repeated warm-ups under load. [web:336]
