import requests
import pandas as pd

SYMBOL = "BTC_USDT"
INTERVAL = "Min60"
RSI_PERIOD = 14

URL = f"https://futures.ourbit.com/api/v1/contract/kline/{SYMBOL}"


def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.rolling(period).mean()
    average_loss = loss.rolling(period).mean()

    rs = average_gain / average_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi


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

    df = pd.DataFrame({
        "time": data["time"],
        "open": data["open"],
        "high": data["high"],
        "low": data["low"],
        "close": data["close"]
    })

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna()

    # RSI 14
    df["RSI14"] = calculate_rsi(
        df["close"],
        RSI_PERIOD
    )

    print()
    print("========== RSI TEST ==========")
    print("Symbol:", SYMBOL)
    print("Timeframe:", INTERVAL)
    print("Candles:", len(df))
    print("RSI Period:", RSI_PERIOD)
    print()
    print(df[["time", "close", "RSI14"]].tail(10).to_string(index=False))
    print()
    print("Current Price:", df["close"].iloc[-1])
    print("Current RSI14:", df["RSI14"].iloc[-1])
    print("==============================")

except Exception as e:

    print("ERROR:", e)
    raise
