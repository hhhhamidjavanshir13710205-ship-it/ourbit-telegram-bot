import requests

SYMBOL = "BTC_USDT"
INTERVAL = "Min60"

URL = f"https://futures.ourbit.com/api/v1/contract/kline/{SYMBOL}"

try:
    response = requests.get(
        URL,
        params={"interval": INTERVAL},
        timeout=30
    )

    print("HTTP:", response.status_code)
    print("RESPONSE:", response.text[:3000])

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise ValueError("Ourbit API returned an error")

    data = result.get("data")

    print()
    print("========== KLINE TEST ==========")
    print("Symbol:", SYMBOL)
    print("Interval:", INTERVAL)
    print("Data type:", type(data))
    print("================================")

except Exception as e:
    print("ERROR:", e)
    raise
