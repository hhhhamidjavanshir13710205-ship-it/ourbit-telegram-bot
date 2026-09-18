import requests
import pandas as pd

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

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise ValueError("Ourbit API returned an error")

    data = result.get("data")

    print("Data type:", type(data))
    print("Data keys:", list(data.keys()))

    # ساخت DataFrame
    df = pd.DataFrame({
        "time": data["time"],
        "open": data["open"],
        "high": data["high"],
        "low": data["low"],
        "close": data["close"]
    })

    # تبدیل قیمت‌ها به عدد
    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna()

    print()
    print("========== KLINE DATA ==========")
    print("Candles:", len(df))
    print()
    print(df.tail(3).to_string(index=False))

    # فقط 20 کندل آخر
    recent = df.tail(20)

    support = recent["low"].min()
    resistance = recent["high"].max()
    price = df["close"].iloc[-1]

    print()
    print("========== SUPPORT / RESISTANCE ==========")
    print("Price:", price)
    print("Support:", support)
    print("Resistance:", resistance)
    print("==========================================")

except Exception as e:
    print("ERROR:", e)
    raise
