# scripts/run_br_nse.py
import json
from app.services.br_nse import fetch_json_data

def main():
    rows = fetch_json_data()
    for row in rows:
        print(json.dumps(row, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
