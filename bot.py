import os
import requests
import traceback

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": text},
        timeout=20
    )

def main():
    try:
        print("STEP 1")

        if not TOKEN:
            raise Exception("TELEGRAM_BOT_TOKEN is missing")

        if not CHAT_ID:
            raise Exception("TELEGRAM_CHAT_ID is missing")

        print("STEP 2")

        response = requests.get(
            "https://api.ourbit.com/api/v1/contract/ticker",
            timeout=20
        )

        print("STEP 3")
        print("HTTP:", response.status_code)

        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict):
            content = data.get("data", data.get("result", data))
        else:
            content = data

        if isinstance(content, list):
            count = len(content)
        else:
            count = 1

        send_telegram(
            "🧪 تست ربات\n\n"
            "✅ GitHub Actions اجرا شد\n"
            "✅ Telegram Secret پیدا شد\n"
            f"📡 Ourbit HTTP: {response.status_code}\n"
            f"📊 تعداد اطلاعات: {count}"
        )

        print("SUCCESS")

    except Exception as e:

        error = traceback.format_exc()

        print(error)

        if TOKEN and CHAT_ID:
            try:
                send_telegram(
                    "❌ خطای ربات\n\n"
                    f"{type(e).__name__}: {e}\n\n"
                    "جزئیات:\n"
                    f"{error[-2500:]}"
                )
            except Exception:
                pass

        raise

if __name__ == "__main__":
    main()
