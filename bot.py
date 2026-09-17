import os
import requests
import time

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOL = "ETHUSDT"
INTERVAL = "15m"

API_URL = (
    f"https://futures.ourbit.com/api/v1/contract/kline/"
    f"{SYMBOL}?interval={INTERVAL}&limit=50"
)

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


def get_candles():
    response = requests.get(
        API_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )

    print("API STATUS:", response.status_code)
    response.raise_for_status()

    data = response.json()
    print("API DATA:", data)

    return data


def send_telegram(message):
    response = requests.post(
        TELEGRAM_URL,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    print("TELEGRAM STATUS:", response.status_code)
    print(response.text)


def main():
    print(f"Starting V3 signal bot: {SYMBOL} / {INTERVAL}")

    try:
        data = get_candles()

        message = (
            f"🟢 V3 TEST\n\n"
            f"Symbol: {SYMBOL}\n"
            f"Timeframe: {INTERVAL}\n\n"
            f"✅ Ourbit API connected\n"
            f"✅ Candle data received\n"
            f"✅ Telegram connected"
        )

        send_telegram(message)

    except Exception as e:
        print("ERROR:", e)

        send_telegram(
            f"🔴 V3 ERROR\n\n"
            f"{SYMBOL} / {INTERVAL}\n\n"
            f"Error:\n{e}"
        )


if __name__ == "__main__":
    main()
