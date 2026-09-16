import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

OURBIT_URL = "https://api.ourbit.com/api/v3/ping"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        },
        timeout=20
    )
    response.raise_for_status()


def main():
    try:
        response = requests.get(OURBIT_URL, timeout=20)
        response.raise_for_status()

        print("OURBIT RESPONSE:", response.text)

        send_telegram(
            "🤖 ربات Ourbit فعال شد ✅\n"
            "📡 اتصال به Ourbit برقرار است."
        )

    except Exception as e:
        print("ERROR:", e)

        send_telegram(
            "❌ خطا در اتصال به Ourbit\n"
            f"{e}"
        )


if __name__ == "__main__":
    main()
