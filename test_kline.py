import requests
import pandas as pd

SYMBOL = "BTC_USDT"
INTERVAL = "Min60"

RSI_PERIOD = 14
NEAR_PERCENT = 0.3

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

        if (
            current_low < df["low"].iloc[i-left:i].min()
            and
            current_low < df["low"].iloc[i+1:i+right+1].min()
        ):
            pivot_lows.append(i)

        if (
            current_high > df["high"].iloc[i-left:i].max()
            and
            current_high > df["high"].iloc[i+1:i+right+1].max()
        ):
            pivot_highs.append(i)

    return pivot_lows, pivot_highs


def detect_divergence(df):

    pivot_lows, pivot_highs = find_pivots(df)

    bullish = False
    bearish = False

    # Bullish divergence
    if len(pivot_lows) >= 2:

        i1 = pivot_lows[-2]
        i2 = pivot_lows[-1]

        price1 = df["low"].iloc[i1]
        price2 = df["low"].iloc[i2]

        rsi1 = df["RSI14"].iloc[i1]
        rsi2 = df["RSI14"].iloc[i2]

        if price2 < price1 and rsi2 > rsi1:
            bullish = True

    # Bearish divergence
    if len(pivot_highs) >= 2:

        i1 = pivot_highs[-2]
        i2 = pivot_highs[-1]

        price1 = df["high"].iloc[i1]
        price2 = df["high"].iloc[i2]

        rsi1 = df["RSI14"].iloc[i1]
        rsi2 = df["RSI14"].iloc[i2]

        if price2 > price1 and rsi2 < rsi1:
            bearish = True

    return bullish, bearish


try:

    # =========================
    # GET KLINE
    # =========================

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

    # =========================
    # DATAFRAME
    # =========================

    df = pd.DataFrame({
        "time": data["time"],
        "open": data["open"],
        "high": data["high"],
        "low": data["low"],
        "close": data["close"]
    })

    for column in [
        "open",
        "high",
        "low",
        "close"
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna()

    # =========================
    # RSI 14
    # =========================

    df["RSI14"] = calculate_rsi(
        df["close"],
        RSI_PERIOD
    )

    df = df.dropna(
        subset=["RSI14"]
    ).reset_index(drop=True)

    # =========================
    # SUPPORT / RESISTANCE
    # =========================

    recent = df.tail(20)

    support = recent["low"].min()
    resistance = recent["high"].max()

    price = df["close"].iloc[-1]

    # =========================
    # DISTANCE
    # =========================

    support_distance = (
        abs(price - support) / support
    ) * 100

    resistance_distance = (
        abs(price - resistance) / resistance
    ) * 100

    # =========================
    # DIVERGENCE
    # =========================

    bullish, bearish = detect_divergence(df)

    # =========================
    # FINAL ALERT LOGIC
    # =========================

    bullish_alert = (
        bullish
        and
        support_distance <= NEAR_PERCENT
    )

    bearish_alert = (
        bearish
        and
        resistance_distance <= NEAR_PERCENT
    )

    # =========================
    # RESULTS
    # =========================

    print()
    print("========== MARKET ==========")
    print("Symbol:", SYMBOL)
    print("Timeframe:", INTERVAL)
    print("Price:", price)
    print("Support:", support)
    print("Resistance:", resistance)
    print("Support Distance:", support_distance, "%")
    print("Resistance Distance:", resistance_distance, "%")
    print("RSI14:", df["RSI14"].iloc[-1])
    print("============================")

    print()
    print("========== DIVERGENCE ==========")
    print("Bullish Divergence:", bullish)
    print("Bearish Divergence:", bearish)
    print("===============================")

    print()
    print("========== FINAL ALERT ==========")
    print("Bullish Alert:", bullish_alert)
    print("Bearish Alert:", bearish_alert)
    print("=================================")

except Exception as e:

    print("ERROR:", e)
    raise

بعد Commit changes بزن و Workflow را اجرا کن.

اگر سبز شد، فقط این خطوط را بفرست:

Price:
Support:
Resistance:
Support Distance:
Resistance Distance:
RSI14:
Bullish Divergence:
Bearish Divergence:
Bullish Alert:
Bearish Alert:

بعد از این تست، اگر همه‌چیز درست بود، می‌ریم سراغ Top 100 ارز.
