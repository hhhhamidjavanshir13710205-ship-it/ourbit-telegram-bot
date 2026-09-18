import requests

URL = "https://futures.ourbit.com/api/v1/contract/ticker"

try:
    response = requests.get(URL, timeout=30)
    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise ValueError("Ourbit API returned an error")

    data = result.get("data", [])

    # مرتب‌سازی بر اساس ارزش معاملات 24 ساعته
    data = sorted(
        data,
        key=lambda x: float(x.get("amount24", 0)),
        reverse=True
    )

    top_100 = data[:100]

    print("========== TOP 100 ==========")
    print("Total contracts:", len(data))
    print("Top 100:", len(top_100))
    print("==============================")

    for i, item in enumerate(top_100, 1):
        print(
            f"{i}. {item.get('symbol')} | "
            f"amount24={item.get('amount24')} | "
            f"volume24={item.get('volume24')}"
        )

except Exception as e:
    print("ERROR:", e)
    raise
