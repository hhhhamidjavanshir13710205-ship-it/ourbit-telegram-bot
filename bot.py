import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

response = requests.post(
    url,
    json={
        "chat_id": CHAT_ID,
        "text": "🧪 تست اتصال ربات\n\n✅ GitHub Actions\n✅ Telegram\n\nاتصال با موفقیت بررسی شد."
    },
    timeout=20
)

print(response.status_code)
print(response.text)
