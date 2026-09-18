import requests
import time
import pandas as pd

TICKER_URL = "https://futures.ourbit.com/api/v1/contract/ticker"

RSI_PERIOD = 14
NEAR_PERCENT = 0.3

non_crypto = {
    "SILVER_USDT",
    "XAU_USDT",
    "XAUT_USDT",
    "AMD_USDT",
    "GOOGL_USDT",
    "SOXL_USDT",
}


def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def find_pivots(df, left=3, right=3):

    lows = []
    highs = []

    for i in range(left, len(df) - right):

        if (
            df["low"].iloc[i] < df["low"].iloc[i-left:i].min()
            and
            df["low"].iloc[i] < df["low"].iloc[i+1:i+right+1].min()
        ):
            lows.append(i)

        if (
            df["high"].iloc[i] > df["high"].iloc[i-left:i].max()
            and
            df["high"].iloc[i] > df["high"].iloc[i+1:i+right+1].max()
        ):
            highs.append(i)

    return lows, highs


def detect_divergence(df):

    pivot_lows, pivot_highs = find_pivots(df)

    bullish = False
    bearish = False

    if len(pivot_lows) >= 2:

        i1 = pivot_lows[-2]
        i2 = pivot_lows[-1]

        if (
            df["low"].iloc[i2] < df["low"].iloc[i1]
            and
            df["RSI14"].iloc[i2] > df["RSI14"].iloc[i1]
        ):
            bullish = True

    if len(pivot_highs) >= 2:

        i1 = pivot_highs[-2]
        i2 = pivot_highs[-1]

        if (
            df["high"].iloc[i2] > df["high"].iloc[i1]
            and
            df["RSI14"].iloc[i2] < df["RSI14"].iloc[i1]
        ):
            bearish = True

    return bullish, bearish


def get_top_100():

    response = requests.get(
        TICKER_URL,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise ValueError("Ticker API error")

    data = result.get("data", [])

    crypto = [
        item for item in data
        if item.get("symbol") not in non_crypto
    ]

    crypto.sort(
        key=lambda x: float(x.get("amount24", 0)),
        reverse=True
    )

    return crypto[:100]


def get_kline(symbol):

    url = (
        f"https://futures.ourbit.com"
        f"/api/v1/contract/kline/{symbol}"
    )

    response = requests.get(
        url,
        params={"interval": "Min60"},
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise ValueError(f"Kline error: {symbol}")

    return result.get("data")


def analyze(symbol):

    data = get_kline(symbol)

    df = pd.DataFrame({
        "time": data["time"],
        "open": data["open"],
        "high": data["high"],
        "low": data["low"],
        "close": data["close"]
    })

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(
            df[col],
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

    recent = df.tail(20)

    price = float(df["close"].iloc[-1])
    support = float(recent["low"].min())
    resistance = float(recent["high"].max())
    rsi = float(df["RSI14"].iloc[-1])

    support_distance = (
        abs(price - support) / support
    ) * 100

    resistance_distance = (
        abs(price - resistance) / resistance
    ) * 100

    bullish, bearish = detect_divergence(df)

    bullish_alert = (
        bullish
        and support_distance <= NEAR_PERCENT
    )

    bearish_alert = (
        bearish
        and resistance_distance <= NEAR_PERCENT
    )

    return {
        "symbol": symbol,
        "price": price,
        "support": support,
        "resistance": resistance,
        "rsi": rsi,
        "bullish": bullish,
        "bearish": bearish,
        "bullish_alert": bullish_alert,
        "bearish_alert": bearish_alert
    }


try:

    top_100 = get_top_100()

    success = 0
    errors = 0
    alerts = []

    print("======================================")
    print("FULL TOP 100 ANALYSIS")
    print("======================================")

    for number, item in enumerate(top_100, 1):

        symbol = item.get("symbol")

        try:

            result = analyze(symbol)

            success += 1

            print(
                f"[{number}/100] {symbol} | "
                f"RSI={result['rsi']:.2f} | "
                f"Bull={result['bullish']} | "
                f"Bear={result['bearish']}"
            )

            if (
                result["bullish_alert"]
                or result["bearish_alert"]
            ):
                alerts.append(result)

        except Exception as e:

            errors += 1

            print(
                f"[{number}/100] {symbol} ERROR: {e}"
            )

        time.sleep(1)

    print()
    print("======================================")
    print("FINAL RESULT")
    print("======================================")
    print("Successful:", success)
    print("Errors:", errors)
    print("Alerts:", len(alerts))
    print("Total:", len(top_100))
    print("======================================")

    if alerts:

        print()
        print("========== ALERT CANDIDATES ==========")

        for alert in alerts:

            print(
                alert["symbol"],
                "| Price:", alert["price"],
                "| Support:", alert["support"],
                "| Resistance:", alert["resistance"],
                "| RSI:", alert["rsi"],
                "| Bull:", alert["bullish"],
                "| Bear:", alert["bearish"]
            )

        print("======================================")

except Exception as e:

    print("FATAL ERROR:", e)
    raise
