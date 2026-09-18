import requests
import time

TICKER_URL = "https://futures.ourbit.com/api/v1/contract/ticker"

non_crypto = {
    "SILVER_USDT",
    "XAU_USDT",
    "XAUT_USDT",
    "AMD_USDT",
    "GOOGL_USDT",
    "SOXL_USDT",
}


def get_top_100():

    response = requests.get(
        TICKER_URL,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise ValueError(
            "Ourbit ticker API returned an error"
        )

    data = result.get("data", [])

    crypto_data = [
        item
        for item in data
        if item.get("symbol") not in non_crypto
    ]

    crypto_data = sorted(
        crypto_data,
        key=lambda x: float(
            x.get("amount24", 0)
        ),
        reverse=True
    )

    return crypto_data[:100]


def get_kline(symbol):

    url = (
        f"https://futures.ourbit.com"
        f"/api/v1/contract/kline/{symbol}"
    )

    response = requests.get(
        url,
        params={
            "interval": "Min60"
        },
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise ValueError(
            f"Kline API error for {symbol}"
        )

    data = result.get("data")

    if not data:
        raise ValueError(
            f"No kline data for {symbol}"
        )

    return data


try:

    top_100 = get_top_100()

    print()
    print("========== TOP 5 KLINE TEST ==========")

    for index, item in enumerate(
        top_100[:5],
        1
    ):

        symbol = item.get("symbol")

        print()
        print(f"{index}. {symbol}")

        data = get_kline(symbol)

        candle_count = len(
            data.get("time", [])
        )

        print(
            "Kline candles:",
            candle_count
        )

        print(
            "Last close:",
            data.get("close", [])[-1]
        )

        print("Status: OK")

        # کمی فاصله بین درخواست‌ها
        time.sleep(1)

    print()
    print("======================================")
    print("5 symbols Kline test completed.")
    print("======================================")

except Exception as e:

    print()
    print("ERROR:", e)
    raise
