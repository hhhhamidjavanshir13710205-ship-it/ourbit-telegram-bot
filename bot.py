import os
import time
import requests
from datetime import datetime, timezone

# =========================
# SETTINGS
# =========================

OURBIT_BASE = "https://contract.ourbit.com"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TIMEFRAME = "Min60"          # 1 hour
RSI_PERIOD = 14
TOP_CONTRACTS = 100
CANDLE_COUNT = 130

# Price must be this close to support/resistance
LEVEL_DISTANCE = 0.006       # 0.6%

# Pivot settings
PIVOT_LEFT = 3
PIVOT_RIGHT = 3

REQUEST_TIMEOUT = 20


# =========================
# HTTP SESSION
# =========================

session = requests.Session()


# =========================
# TELEGRAM
# =========================

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram secrets are missing.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = session.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        },
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()
    return True


# =========================
# OURBIT REQUEST
# =========================

def ourbit_get(path, params=None):
    url = OURBIT_BASE + path

    response = session.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()
    return response.json()


# =========================
# HELPERS
# =========================

def unwrap_data(response):
    """
    Handles common API structures:
    {
        "data": [...]
    }

    or

    {
        "success": true,
        "data": [...]
    }
    """

    if isinstance(response, dict):
        if "data" in response:
            return response["data"]

        if "result" in response:
            return response["result"]

    return response


def number(value):
    try:
        return float(value)
    except Exception:
        return None


# =========================
# GET ALL FUTURES TICKERS
# =========================

def get_tickers():

    response = ourbit_get(
        "/api/v1/contract/ticker"
    )

    data = unwrap_data(response)

    if not isinstance(data, list):
        print("Unexpected ticker response:")
        print(response)
        return []

    tickers = []

    for item in data:

        if not isinstance(item, dict):
            continue

        symbol = (
            item.get("symbol")
            or item.get("contract")
        )

        if not symbol:
            continue

        last_price = (
            item.get("lastPrice")
            or item.get("last_price")
            or item.get("last")
            or item.get("price")
        )

        volume = (
            item.get("volume")
            or item.get("vol")
            or item.get("quantity")
            or item.get("amount")
        )

        last_price = number(last_price)
        volume = number(volume)

        if last_price is None:
            continue

        if volume is None:
            volume = 0

        tickers.append({
            "symbol": symbol,
            "price": last_price,
            "volume": volume
        })

    return tickers


# =========================
# TOP 100 BY 24H VOLUME
# =========================

def get_top_contracts():

    tickers = get_tickers()

    tickers.sort(
        key=lambda x: x["volume"],
        reverse=True
    )

    top = tickers[:TOP_CONTRACTS]

    print(f"Found {len(tickers)} futures contracts.")
    print(f"Checking top {len(top)} by volume.")

    return top


# =========================
# GET KLINES
# =========================

def get_klines(symbol):

    now_ms = int(time.time() * 1000)

    # 130 hours of history
    start_ms = now_ms - (CANDLE_COUNT * 60 * 60 * 1000)

    response = ourbit_get(
        f"/api/v1/contract/kline/{symbol}",
        params={
            "interval": TIMEFRAME,
            "start": start_ms,
            "end": now_ms
        }
    )

    data = unwrap_data(response)

    if isinstance(data, dict):

        # Some APIs wrap candle arrays inside a key
        for key in ["data", "list", "rows", "klines"]:
            if key in data:
                data = data[key]
                break

    if not isinstance(data, list):
        return []

    candles = []

    for row in data:

        try:

            if isinstance(row, list):

                # Standard futures kline structure:
                # [time, open, close, high, low, volume, amount]

                if len(row) < 6:
                    continue

                timestamp = number(row[0])
                open_price = number(row[1])
                close_price = number(row[2])
                high_price = number(row[3])
                low_price = number(row[4])
                volume = number(row[5])

            elif isinstance(row, dict):

                timestamp = number(
                    row.get("time")
                    or row.get("timestamp")
                    or row.get("ts")
                )

                open_price = number(
                    row.get("open")
                    or row.get("openPrice")
                )

                close_price = number(
                    row.get("close")
                    or row.get("closePrice")
                )

                high_price = number(
                    row.get("high")
                    or row.get("highPrice")
                )

                low_price = number(
                    row.get("low")
                    or row.get("lowPrice")
                )

                volume = number(
                    row.get("volume")
                    or row.get("vol")
                )

            else:
                continue

            if None in (
                timestamp,
                open_price,
                close_price,
                high_price,
                low_price
            ):
                continue

            candles.append({
                "time": timestamp,
                "open": open_price,
                "close": close_price,
                "high": high_price,
                "low": low_price,
                "volume": volume or 0
            })

        except Exception:
            continue

    candles.sort(key=lambda x: x["time"])

    return candles[-CANDLE_COUNT:]


# =========================
# RSI
# =========================

def calculate_rsi(closes, period=14):

    if len(closes) < period + 1:
        return []

    gains = []
    losses = []

    for i in range(1, len(closes)):

        change = closes[i] - closes[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi = [None] * period

    if avg_loss == 0:
        rsi.append(100)
    else:
        rs = avg_gain / avg_loss
        rsi.append(100 - (100 / (1 + rs)))

    for i in range(period, len(gains)):

        avg_gain = (
            (avg_gain * (period - 1)) + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1)) + losses[i]
        ) / period

        if avg_loss == 0:
            value = 100
        else:
            rs = avg_gain / avg_loss
            value = 100 - (100 / (1 + rs))

        rsi.append(value)

    return rsi


# =========================
# PIVOTS
# =========================

def find_pivot_lows(candles):

    pivots = []

    for i in range(
        PIVOT_LEFT,
        len(candles) - PIVOT_RIGHT
    ):

        current = candles[i]["low"]

        left = [
            candles[j]["low"]
            for j in range(
                i - PIVOT_LEFT,
                i
            )
        ]

        right = [
            candles[j]["low"]
            for j in range(
                i + 1,
                i + PIVOT_RIGHT + 1
            )
        ]

        if current <= min(left) and current <= min(right):
            pivots.append(i)

    return pivots


def find_pivot_highs(candles):

    pivots = []

    for i in range(
        PIVOT_LEFT,
        len(candles) - PIVOT_RIGHT
    ):

        current = candles[i]["high"]

        left = [
            candles[j]["high"]
            for j in range(
                i - PIVOT_LEFT,
                i
            )
        ]

        right = [
            candles[j]["high"]
            for j in range(
                i + 1,
                i + PIVOT_RIGHT + 1
            )
        ]

        if current >= max(left) and current >= max(right):
            pivots.append(i)

    return pivots


# =========================
# SUPPORT / RESISTANCE
# =========================

def get_support_resistance(candles):

    lows = find_pivot_lows(candles)
    highs = find_pivot_highs(candles)

    if not lows or not highs:
        return None, None

    current_price = candles[-1]["close"]

    supports = [
        candles[i]["low"]
        for i in lows
        if candles[i]["low"] <= current_price
    ]

    resistances = [
        candles[i]["high"]
        for i in highs
        if candles[i]["high"] >= current_price
    ]

    support = max(supports) if supports else None
    resistance = min(resistances) if resistances else None

    return support, resistance


# =========================
# NEAR LEVEL
# =========================

def near_level(price, level):

    if level is None:
        return False

    distance = abs(price - level) / level

    return distance <= LEVEL_DISTANCE


# =========================
# RSI DIVERGENCE
# =========================

def detect_divergence(candles, rsi):

    if len(candles) != len(rsi):
        return None

    lows = find_pivot_lows(candles)
    highs = find_pivot_highs(candles)

    # Bullish divergence:
    # price makes lower low
    # RSI makes higher low

    if len(lows) >= 2:

        i1 = lows[-2]
        i2 = lows[-1]

        if (
            rsi[i1] is not None
            and rsi[i2] is not None
        ):

            price_lower = (
                candles[i2]["low"]
                < candles[i1]["low"]
            )

            rsi_higher = (
                rsi[i2]
                > rsi[i1]
            )

            if price_lower and rsi_higher:
                return "BULLISH"


    # Bearish divergence:
    # price makes higher high
    # RSI makes lower high

    if len(highs) >= 2:

        i1 = highs[-2]
        i2 = highs[-1]

        if (
            rsi[i1] is not None
            and rsi[i2] is not None
        ):

            price_higher = (
                candles[i2]["high"]
                > candles[i1]["high"]
            )

            rsi_lower = (
                rsi[i2]
                < rsi[i1]
            )

            if price_higher and rsi_lower:
                return "BEARISH"

    return None


# =========================
# ANALYZE ONE CONTRACT
# =========================

def analyze(symbol, ticker_price):

    candles = get_klines(symbol)

    if len(candles) < 50:
        return None

    closes = [
        candle["close"]
        for candle in candles
    ]

    rsi = calculate_rsi(
        closes,
        RSI_PERIOD
    )

    if not rsi:
        return None

    support, resistance = get_support_resistance(
        candles
    )

    price = ticker_price

    divergence = detect_divergence(
        candles,
        rsi
    )

    alerts = []

    if near_level(price, support):

        alerts.append({
            "type": "SUPPORT",
            "level": support
        })

        if divergence == "BULLISH":

            alerts.append({
                "type": "BULLISH_DIVERGENCE",
                "level": support
            })

    if near_level(price, resistance):

        alerts.append({
            "type": "RESISTANCE",
            "level": resistance
        })

        if divergence == "BEARISH":

            alerts.append({
                "type": "BEARISH_DIVERGENCE",
                "level": resistance
            })

    if not alerts:
        return None

    return {
        "symbol": symbol,
        "price": price,
        "support": support,
        "resistance": resistance,
        "rsi": rsi[-1],
        "alerts": alerts
    }


# =========================
# FORMAT ALERT
# =========================

def format_alert(result):

    symbol = result["symbol"]
    price = result["price"]
    support = result["support"]
    resistance = result["resistance"]
    rsi = result["rsi"]

    lines = [
        "🚨 OURBIT FUTURES ALERT 🚨",
        "",
        f"📌 قرارداد: {symbol}",
        f"💰 قیمت: {price:.8g}",
    ]

    if support is not None:
        lines.append(
            f"🟢 حمایت: {support:.8g}"
        )

    if resistance is not None:
        lines.append(
            f"🔴 مقاومت: {resistance:.8g}"
        )

    if rsi is not None:
        lines.append(
            f"📊 RSI(14): {rsi:.2f}"
        )

    lines.append("")

    for alert in result["alerts"]:

        if alert["type"] == "SUPPORT":

            lines.append(
                "🟢 قیمت به محدوده حمایت رسیده است."
            )

        elif alert["type"] == "RESISTANCE":

            lines.append(
                "🔴 قیمت به محدوده مقاومت رسیده است."
            )

        elif alert["type"] == "BULLISH_DIVERGENCE":

            lines.append(
                "🟢 واگرایی مثبت RSI در حمایت شناسایی شد."
            )

        elif alert["type"] == "BEARISH_DIVERGENCE":

            lines.append(
                "🔴 واگرایی منفی RSI در مقاومت شناسایی شد."
            )

    lines.extend([
        "",
        "⏱ تایم‌فریم: 1H",
        "🤖 فقط هشدار — بدون معامله"
    ])

    return "\n".join(lines)


# =========================
# MAIN
# =========================

def main():

    print("=" * 50)
    print("OURBIT FUTURES ALERT BOT")
    print("=" * 50)

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "Telegram secrets are missing."
        )

    top_contracts = get_top_contracts()

    if not top_contracts:
        raise RuntimeError(
            "No futures contracts received from Ourbit."
        )

    alert_count = 0

    for index, ticker in enumerate(top_contracts, start=1):

        symbol = ticker["symbol"]
        price = ticker["price"]

        print(
            f"[{index}/{len(top_contracts)}] "
            f"{symbol} -> {price}"
        )

        try:

            result = analyze(
                symbol,
                price
            )

            if result:

                message = format_alert(result)

                print(message)

                send_telegram(message)

                alert_count += 1

        except Exception as e:

            print(
                f"ERROR {symbol}: {e}"
            )

        # Small pause to avoid hammering the API
        time.sleep(0.15)

    print(
        f"Finished. Alerts sent: {alert_count}"
    )


if __name__ == "__main__":
    main()
