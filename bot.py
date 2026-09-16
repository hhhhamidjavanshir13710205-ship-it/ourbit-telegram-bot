import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

OURBIT_URL = "https://contract.ourbit.com/api/v1/contract/ticker"


def telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    response.raise_for_status()


def main():

    if not TOKEN or not CHAT_ID:
        raise Exception("Telegram secrets are missing")

    # Test Ourbit Futures
    response = requests.get(
        OURBIT_URL,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    # فقط تعداد اطلاعات دریافتی را گزارش می‌کنیم
    if isinstance(data, dict):
        content = data.get("data", data.get("result", data))
    else:
        content = data

    if isinstance(content, list):
        count = len(content)
    else:
        count = 1

    message = (
        "🤖 ربات Ourbit فعال شد ✅\n\n"
        "📡 اتصال به Ourbit Futures برقرار است.\n"
        f"📊 اطلاعات دریافت‌شده: {count}\n\n"
        "🧪 تست اولیه موفق بود."
    )

    telegram(message)


if __name__ == "__main__":
    main()
