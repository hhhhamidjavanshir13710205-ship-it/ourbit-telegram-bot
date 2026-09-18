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

    return 100 - (100 / (1 + rs))


def find_pivots(df, left=3, right=3):

    pivot_lows = []
    pivot_highs = []

    for i in range(left, len(df) - right):

        current_low = df["low"].iloc[i]
        current_high = df["high"].iloc[i]

        left_lows = df["low"].iloc[i-left:i]
        right_lows = df["low"].iloc[i+1:i+right+1]

        left_highs = df["high"].iloc[i-left:i]
        right_highs = df["high"].iloc[i+1:i+right+1]

        if current_low < left_lows.min() and current_low < right_lows.min():
            pivot_lows.append(i)

        if current_high > left_highs.max() and current_high > right_highs.max():
            pivot_highs.append(i)

    return pivot_lows, pivot_highs


def detect_divergence(df):

    pivot_lows, pivot_highs = find_pivots(df)

    bullish = False
    bearish = False

    bullish_info = None
    bearish_info = None

    # Bullish divergence:
    # Price makes a lower low
    # RSI makes a higher low

    if len(pivot_lows) >= 2:

        i1 = pivot_lows[-2]
        i2 = pivot_lows[-1]

        price1 = df["low"].iloc[i1]
        price2 = df["low"].iloc[i2]

        rsi1 = df["RSI14"].iloc[i1]
        rsi2 = df["RSI14"].iloc[i2]

        if (
            price2 < price1
            and rsi2 > rsi1
        ):
            bullish = True

            bullish_info = (
                i1,
                i2,
                price1,
                price2,
                rsi1,
                rsi2
            )

    # Bearish divergence:
    # Price makes a higher high
    # RSI makes a lower high

    if len(pivot_highs) >= 2:

        i1 = pivot_highs[-2]
        i2 = pivot_highs[-1]

        price1 = df["high"].iloc[i1]
        price2 = df["high"].iloc[i2]

        rsi1 = df["RSI14"].iloc[i1]
        rsi2 = df["RSI14"].iloc[i2]

        if (
            price2 > price1
            and rsi2 < rsi1
        ):
            bearish = True

            bearish_info = (
                i1,
                i2,
                price1,
                price2,
                rsi1,
                rsi2
            )

    return bullish, bearish, bullish_info, bearish_info


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

    df["RSI14"] = calculate_rsi(
        df["close"],
        RSI_PERIOD
    )

    df = df.dropna(
        subset=["RSI14"]
    ).reset_index(drop=True)

    bullish, bearish, bullish_info, bearish_info = detect_divergence(df)

    print()
    print("========== DIVERGENCE TEST ==========")
    print("Symbol:", SYMBOL)
    print("Timeframe:", INTERVAL)
    print("Candles:", len(df))
    print()

    print("Bullish Divergence:", bullish)
    print("Bearish Divergence:", bearish)

    if bullish_info:

        print()
        print("========== BULLISH DETAILS ==========")

        _, _, price1, price2, rsi1, rsi2 = bullish_info

        print("Previous Price Low:", price1)
        print("Latest Price Low:", price2)
        print("Previous RSI:", rsi1)
        print("Latest RSI:", rsi2)

    if bearish_info:

        print()
        print("========== BEARISH DETAILS ==========")

        _, _, price1, price2, rsi1, rsi2 = bearish_info

        print("Previous Price High:", price1)
        print("Latest Price High:", price2)
        print("Previous RSI:", rsi1)
        print("Latest RSI:", rsi2)

    print("=====================================")

except Exception as e:

    print("ERROR:", e)
    raise
