# file: scripts/bot_check.py
import os
import socket
from datetime import datetime
import requests

from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise SystemExit("BOT_TOKEN or CHAT_ID not set in environment")

host = socket.gethostname()
script_path = os.path.abspath(__file__)
dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

text = f"Host : {host}\nScript : {script_path}\nBot test at {dt} !"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": text,
}

# application/x-www-form-urlencoded like the PowerShell script
resp = requests.post(url, data=payload, timeout=20)
resp.raise_for_status()
print(resp.json())
