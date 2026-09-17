import os
import requests
import time

# =========================
# SETTINGS
# =========================

SYMBOL = "ETH_USDT"
INTERVAL = "Min15"
NEAR_PERCENT = 0.3

OURBIT_URL = (
    "https://contract.ourbit.com/"
    "api/v1/contract/kline/ETH_USDT"
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# =========================
# TELEGRAM
# =========================

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram secrets are missing.")
        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(
            url,
            data=data,
            timeout=20
        )

        print("Telegram response:", response.text)

        return response.ok

    except Exception as e:
        print("Telegram error:", e)
        return False


# =========================
# OURBIT API
# =========================

def get_klines():
    print()
    print("========== OURBIT REQUEST ==========")
    print("URL:", OURBIT_URL)
    print("Symbol:", SYMBOL)
    print("Interval:", INTERVAL)
    print("====================================")

    try:
        params = {
            "interval": INTERVAL
        }

        response = requests.get(
            OURBIT_URL,
            params=params,
            timeout=30
        )

        print("HTTP STATUS:", response.status_code)
        print("RESPONSE:", response.text[:1000])

        response.raise_for_status()

        return response.json()

    except Exception as e:
        print("Ourbit request error:", e)
        return None


# =========================
# MAIN
# =========================

def main():

    print("====================================")
    print("Starting Ourbit Crypto Bot")
    print("Symbol:", SYMBOL)
    print("Timeframe:", INTERVAL)
    print("Near:", NEAR_PERCENT, "%")
    print("====================================")

    data = get_klines()

    if data is None:
        print()
        print("========== ERROR ==========")
        print("Ourbit API could not be reached.")
        print("============================")
        return

    print()
    print("========== API OK ==========")
    print(data)
    print("============================")

    # فعلاً فقط تست اتصال انجام می‌دهیم.
    # بعد از اینکه اتصال API تأیید شد،
    # منطق Support / Resistance را اضافه می‌کنیم.


if __name__ == "__main__":
    main()
