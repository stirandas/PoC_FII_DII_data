# app/tests/test_update.py
from datetime import date
from app.services.upd_data import touch_timestamp

def main():
    run_dt = date(2025, 10, 3)  # pick the target PK date
    count = touch_timestamp(run_dt)
    if count == 1:
        print("Timestamp updated for", run_dt)
    elif count == 0:
        print("No row found for", run_dt, "- nothing updated")
    else:
        print("Updated", count, "rows for", run_dt)  # defensive, should not happen for a PK

if __name__ == "__main__":
    main()
