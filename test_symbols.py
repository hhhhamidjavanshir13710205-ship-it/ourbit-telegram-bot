import requests

URL = "https://futures.ourbit.com/api/v1/contract/ticker"

# نمادهایی که فعلاً می‌خواهیم از لیست کریپتو حذف کنیم
non_crypto = {
    "SILVER_USDT",
    "XAU_USDT",
    "XAUT_USDT",
    "AMD_USDT",
    "GOOGL_USDT",
    "SOXL_USDT",
}

try:

    response = requests.get(
        URL,
        timeout=30
    )

    print("HTTP:", response.status_code)

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise ValueError(
            "Ourbit API returned an error"
        )

    data = result.get("data", [])

    print()
    print("========== OURBIT SYMBOLS ==========")
    print("Total contracts:", len(data))

    # حذف نمادهای غیرکریپتویی
    crypto_data = [
        item
        for item in data
        if item.get("symbol") not in non_crypto
    ]

    print("Crypto contracts:", len(crypto_data))

    # مرتب‌سازی بر اساس ارزش معاملات 24 ساعته
    crypto_data = sorted(
        crypto_data,
        key=lambda x: float(
            x.get("amount24", 0)
        ),
        reverse=True
    )

    top_100 = crypto_data[:100]

    print("Top 100:", len(top_100))
    print("====================================")

    print()

    print("========== TOP 100 ==========")

    for i, item in enumerate(
        top_100,
        1
    ):

        print(
            f"{i}. "
            f"{item.get('symbol')} | "
            f"amount24={item.get('amount24')}"
        )

    print("==============================")

except Exception as e:

    print("ERROR:", e)
    raise
