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
    print("======================================")
    print("TOP 100 KLINE TEST")
    print("======================================")

    success_count = 0
    error_count = 0

    for index, item in enumerate(
        top_100,
        1
    ):

        symbol = item.get("symbol")

        print()
        print(
            f"[{index}/100] {symbol}"
        )

        try:

            data = get_kline(symbol)

            candles = len(
                data.get("time", [])
            )

            closes = data.get(
                "close",
                []
            )

            if not closes:
                raise ValueError(
                    "No close prices"
                )

            last_close = closes[-1]

            print(
                "Kline candles:",
                candles
            )

            print(
                "Last close:",
                last_close
            )

            print("Status: OK")

            success_count += 1

        except Exception as e:

            print(
                "Status: ERROR"
            )

            print(
                "Error:",
                e
            )

            error_count += 1

        # فاصله بین درخواست‌ها
        time.sleep(1)

    print()
    print("======================================")
    print("FINAL RESULT")
    print("======================================")
    print(
        "Successful:",
        success_count
    )
    print(
        "Errors:",
        error_count
    )
    print(
        "Total:",
        len(top_100)
    )
    print("======================================")


except Exception as e:

    print()
    print("FATAL ERROR:", e)
    raise
