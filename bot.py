import os
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# SETTINGS
# =========================

TICKER_URL = "https://futures.ourbit.com/api/v1/contract/ticker"
KLINE_URL = "https://futures.ourbit.com/api/v1/contract/kline"

INTERVAL = "Min60"
RSI_PERIOD = 14
NEAR_PERCENT = 0.3

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

NON_CRYPTO = {
    "SILVER_USDT",
    "XAU_USDT",
    "XAUT_USDT",
    "AMD_USDT",
    "GOOGL_USDT",
    "SOXL_USDT",
}


# =========================
# TELEGRAM
# =========================

def send_telegram_photo(image_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram secrets are missing.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    try:
        with open(image_path, "rb") as photo:
            response = requests.post(
                url,
                data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "caption": caption
                },
                files={
                    "photo": photo
                },
                timeout=30
            )

        print("Telegram status:", response.status_code)
        print("Telegram response:", response.text[:500])

        return response.ok

    except Exception as e:
        print("Telegram photo error:", e)
        return False


# =========================
# GET TOP 100
# =========================

def get_top_100():

    print("========== GET TOP 100 ==========")

    response = requests.get(
        TICKER_URL,
        timeout=30
    )

    print("Ticker HTTP:", response.status_code)

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise ValueError("Ticker API error")

    data = result.get("data", [])

    crypto = [
        item
        for item in data
        if item.get("symbol") not in NON_CRYPTO
    ]

    crypto.sort(
        key=lambda x: float(x.get("amount24", 0)),
        reverse=True
    )

    top_100 = crypto[:100]

    print("Total contracts:", len(data))
    print("Top 100:", len(top_100))

    return top_100


# =========================
# GET KLINES
# =========================

def get_kline(symbol):

    url = f"{KLINE_URL}/{symbol}"

    response = requests.get(
        url,
        params={
            "interval": INTERVAL
        },
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise ValueError(f"Kline error: {symbol}")

    return result.get("data")


# =========================
# DATAFRAME
# =========================

def make_dataframe(data):

    if not data or not isinstance(data, dict):
        return None

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

    df = df.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close"
        ]
    )

    return df.reset_index(drop=True)


# =========================
# RSI
# =========================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi


# =========================
# PIVOTS
# =========================

def find_pivots(df, left=3, right=3):

    pivot_lows = []
    pivot_highs = []

    for i in range(
        left,
        len(df) - right
    ):

        current_low = df["low"].iloc[i]
        current_high = df["high"].iloc[i]

        left_lows = df["low"].iloc[
            i-left:i
        ]

        right_lows = df["low"].iloc[
            i+1:i+right+1
        ]

        left_highs = df["high"].iloc[
            i-left:i
        ]

        right_highs = df["high"].iloc[
            i+1:i+right+1
        ]

        if (
            current_low < left_lows.min()
            and
            current_low < right_lows.min()
        ):
            pivot_lows.append(i)

        if (
            current_high > left_highs.max()
            and
            current_high > right_highs.max()
        ):
            pivot_highs.append(i)

    return pivot_lows, pivot_highs


# =========================
# DIVERGENCE
# =========================

def detect_divergence(df):

    pivot_lows, pivot_highs = find_pivots(df)

    bullish = False
    bearish = False

    bullish_points = None
    bearish_points = None

    # Bullish divergence:
    # Price makes lower low
    # RSI makes higher low

    if len(pivot_lows) >= 2:

        i1 = pivot_lows[-2]
        i2 = pivot_lows[-1]

        price1 = df["low"].iloc[i1]
        price2 = df["low"].iloc[i2]

        rsi1 = df["RSI14"].iloc[i1]
        rsi2 = df["RSI14"].iloc[i2]

        if (
            price2 < price1
            and
            rsi2 > rsi1
        ):
            bullish = True
            bullish_points = (i1, i2)

    # Bearish divergence:
    # Price makes higher high
    # RSI makes lower high

    if len(pivot_highs) >= 2:

        i1 = pivot_highs[-2]
        i2 = pivot_highs[-1]

        price1 = df["high"].iloc[i1]
        price2 = df["high"].iloc[i2]

        rsi1 = df["RSI14"].iloc[i1]
        rsi2 = df["RSI14"].iloc[i2]

        if (
            price2 > price1
            and
            rsi2 < rsi1
        ):
            bearish = True
            bearish_points = (i1, i2)

    return (
        bullish,
        bearish,
        bullish_points,
        bearish_points
    )


# =========================
# SUPPORT / RESISTANCE
# =========================

def calculate_support_resistance(df):

    pivot_lows, pivot_highs = find_pivots(df)

    if not pivot_lows or not pivot_highs:
        return None, None

    current_price = float(
        df["close"].iloc[-1]
    )

    supports = [
        float(df["low"].iloc[i])
        for i in pivot_lows
        if df["low"].iloc[i] <= current_price
    ]

    resistances = [
        float(df["high"].iloc[i])
        for i in pivot_highs
        if df["high"].iloc[i] >= current_price
    ]

    if not supports:
        supports = [
            float(df["low"].iloc[i])
            for i in pivot_lows
        ]

    if not resistances:
        resistances = [
            float(df["high"].iloc[i])
            for i in pivot_highs
        ]

    support = max(supports)
    resistance = min(resistances)

    return support, resistance


# =========================
# CREATE CHART
# =========================

def create_chart(
    symbol,
    df,
    support,
    resistance,
    bullish,
    bearish,
    bullish_points,
    bearish_points
):

    chart_df = df.tail(100).copy()

    fig = plt.figure(
        figsize=(14, 9)
    )

    grid = fig.add_gridspec(
        2,
        1,
        height_ratios=[3, 1]
    )

    ax_price = fig.add_subplot(
        grid[0]
    )

    ax_rsi = fig.add_subplot(
        grid[1],
        sharex=ax_price
    )

    # Candles

    for i, row in chart_df.iterrows():

        if row["close"] >= row["open"]:
            candle_color = "green"
        else:
            candle_color = "red"

        ax_price.vlines(
            i,
            row["low"],
            row["high"],
            color=candle_color,
            linewidth=1
        )

        body_bottom = min(
            row["open"],
            row["close"]
        )

        body_height = abs(
            row["close"] - row["open"]
        )

        if body_height == 0:
            body_height = (
                row["close"] * 0.0001
            )

        ax_price.bar(
            i,
            body_height,
            bottom=body_bottom,
            width=0.7,
            color=candle_color
        )

    # Support / Resistance

    ax_price.axhline(
        support,
        linestyle="--",
        linewidth=1.5,
        label=f"Support {support:.6g}"
    )

    ax_price.axhline(
        resistance,
        linestyle="--",
        linewidth=1.5,
        label=f"Resistance {resistance:.6g}"
    )

    # Current price

    current_price = float(
        df["close"].iloc[-1]
    )

    ax_price.axhline(
        current_price,
        linestyle=":",
        linewidth=1,
        label=f"Price {current_price:.6g}"
    )

    # Divergence markers

    visible_start = len(df) - len(chart_df)

    if bullish and bullish_points:

        p1, p2 = bullish_points

        if p1 >= visible_start:
            ax_price.scatter(
                p1,
                df["low"].iloc[p1],
                marker="^",
                s=100,
                label="Bullish Divergence"
            )

        if p2 >= visible_start:
            ax_price.scatter(
                p2,
                df["low"].iloc[p2],
                marker="^",
                s=100
            )

    if bearish and bearish_points:

        p1, p2 = bearish_points

        if p1 >= visible_start:
            ax_price.scatter(
                p1,
                df["high"].iloc[p1],
                marker="v",
                s=100,
                label="Bearish Divergence"
            )

        if p2 >= visible_start:
            ax_price.scatter(
                p2,
                df["high"].iloc[p2],
                marker="v",
                s=100
            )

    # RSI

    ax_rsi.plot(
        chart_df.index,
        chart_df["RSI14"]
    )

    ax_rsi.axhline(
        70,
        linestyle="--",
        linewidth=1
    )

    ax_rsi.axhline(
        30,
        linestyle="--",
        linewidth=1
    )

    ax_rsi.set_ylim(
        0,
        100
    )

    ax_rsi.set_ylabel(
        "RSI 14"
    )

    # Title

    alert_type = ""

    if bearish:
        alert_type = "BEARISH DIVERGENCE / RESISTANCE"

    elif bullish:
        alert_type = "BULLISH DIVERGENCE / SUPPORT"

    ax_price.set_title(
        f"{symbol.replace('_USDT', '')} | 1H | {alert_type}"
    )

    ax_price.set_ylabel(
        "Price"
    )

    ax_price.grid(
        alpha=0.2
    )

    ax_rsi.grid(
        alpha=0.2
    )

    ax_price.legend(
        loc="upper left",
        fontsize=8
    )

    plt.tight_layout()

    image_path = f"/tmp/{symbol}_alert.png"

    plt.savefig(
        image_path,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)

    return image_path


# =========================
# ANALYZE SYMBOL
# =========================

def analyze_symbol(symbol):

    data = get_kline(symbol)

    df = make_dataframe(data)

    if df is None or len(df) < 100:
        raise ValueError(
            f"Not enough data: {symbol}"
        )

    df["RSI14"] = calculate_rsi(
        df["close"],
        RSI_PERIOD
    )

    df = df.dropna(
        subset=["RSI14"]
    ).reset_index(drop=True)

    price = float(
        df["close"].iloc[-1]
    )

    support, resistance = (
        calculate_support_resistance(df)
    )

    if support is None or resistance is None:
        return None

    support_distance = (
        abs(price - support)
        / support
    ) * 100

    resistance_distance = (
        abs(price - resistance)
        / resistance
    ) * 100

    (
        bullish,
        bearish,
        bullish_points,
        bearish_points
    ) = detect_divergence(df)

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

    if not bullish_alert and not bearish_alert:
        return None

    return {
        "symbol": symbol,
        "df": df,
        "price": price,
        "support": support,
        "resistance": resistance,
        "support_distance": support_distance,
        "resistance_distance": resistance_distance,
        "rsi": float(df["RSI14"].iloc[-1]),
        "bullish": bullish,
        "bearish": bearish,
        "bullish_points": bullish_points,
        "bearish_points": bearish_points
    }


# =========================
# MAIN
# =========================

def main():

    print("====================================")
    print("OURBIT FUTURES ALERT BOT")
    print("Timeframe: 1H")
    print("Top 100")
    print("RSI: 14")
    print("====================================")

    top_100 = get_top_100()

    alerts = []

    for number, item in enumerate(
        top_100,
        start=1
    ):

        symbol = item.get("symbol")

        print(
            f"[{number}/100] Checking {symbol}"
        )

        try:

            result = analyze_symbol(
                symbol
            )

            if result:

                alerts.append(
                    result
                )

                print(
                    ">>> ALERT:",
                    symbol
                )

            else:

                print(
                    "No alert:",
                    symbol
                )

        except Exception as e:

            print(
                f"ERROR {symbol}:",
                e
            )

        time.sleep(0.2)

    print("====================================")
    print(
        "TOTAL ALERTS:",
        len(alerts)
    )
    print("====================================")

    # Send every alert

    for alert in alerts:

        symbol = alert["symbol"]

        if alert["bearish"]:

            alert_name = (
                "🔴 واگرایی نزولی نزدیک مقاومت"
            )

        else:

            alert_name = (
                "🟢 واگرایی صعودی نزدیک حمایت"
            )

        caption = (
            f"{alert_name}\n\n"
            f"💰 ارز: {symbol.replace('_USDT', '')}/USDT\n"
            f"💵 قیمت: {alert['price']:.8g}\n"
            f"📊 RSI 14: {alert['rsi']:.2f}\n"
            f"🟢 حمایت: {alert['support']:.8g}\n"
            f"🔴 مقاومت: {alert['resistance']:.8g}\n"
            f"📏 فاصله حمایت: "
            f"{alert['support_distance']:.3f}%\n"
            f"📏 فاصله مقاومت: "
            f"{alert['resistance_distance']:.3f}%\n"
            f"⏱ تایم‌فریم: 1H"
        )

        image_path = create_chart(
            symbol,
            alert["df"],
            alert["support"],
            alert["resistance"],
            alert["bullish"],
            alert["bearish"],
            alert["bullish_points"],
            alert["bearish_points"]
        )

        print(
            "Sending Telegram:",
            symbol
        )

        send_telegram_photo(
            image_path,
            caption
        )

    print("====================================")
    print("BOT FINISHED")
    print("====================================")


if __name__ == "__main__":
    main()
