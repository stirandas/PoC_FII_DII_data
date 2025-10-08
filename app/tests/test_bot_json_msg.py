# app/tests/test_bot_json_msg.py
from app.services.bot_json_msg import bot_json_msg, TelegramSendError

def main():
    payload = [
        {
            "Category": "DII-test **",
            "Date": "06-Oct-2025",
            "Buy Value(₹ Crores)": "15,515.91",
            "Sell Value (₹ Crores)": "10,634.31",
            "Net Value (₹ Crores)": "4,881.60",
        },
        {
            "Category": "FII/FPI-test *",
            "Date": "06-Oct-2025",
            "Buy Value(₹ Crores)": "10,712.57",
            "Sell Value (₹ Crores)": "10,926.11",
            "Net Value (₹ Crores)": "-213.54",
        },
    ]

    try:
        bot_json_msg(payload)
        print("Sent")
    except TelegramSendError as e:
        print("Failed:", e)

if __name__ == "__main__":
    main()
