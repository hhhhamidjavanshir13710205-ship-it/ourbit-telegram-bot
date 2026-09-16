import os
import time
import requests
import traceback
from datetime import datetime, timezone

# =========================
# SETTINGS
# =========================

BASE_URL = "https://futures.ourbit.com"

TICKER_URL = f"{BASE_URL}/api/v1/contract/ticker"

# Endpoint کندل 1 ساعته
KLINE_URL = f"{BASE_URL}/api/v1/contract/kline"

TELEGRAM_URL = "https://api.telegram.org/bot{}/sendMessage"

TOP_N = 100
TIMEFRAME = "1h"

RSI_PERIOD = 14

# تعداد کندل مورد نیاز برای تحلیل
CANDLE_LIMIT = 100

# فقط وقتی قیمت به محدوده S/R نزدیک باشد هشدار می‌دهیم
SR_DISTANCE_PERCENT = 0.5

# حداقل فاصله بین هشدارهای یک نماد در همان اجرا
SLEEP_BETWEEN_REQUESTS = 0.05


# =========================
# ENV
# =========================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# =========================
# TELEGRAM
# =========================

def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        raise Exception("Telegram secrets are missing")

    url = TELEGRAM_URL.format(TOKEN)

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text
        },
        timeout=20
    )

    response.raise_for_status()


# =========================
# HTTP
# =========================

def get_json(url, params=None):
    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    return response.json()


# =========================
# DATA HELPERS
# =========================

def unwrap_data(data):
    """
    Ourbit ممکن است داده را داخل data یا result قرار دهد.
    """

    if isinstance(data, dict):

        if "data" in data:
            return data["data"]

        if "result" in data:
            return data["result"]

    return data


def number(value):
    try:
        return float(value)
    except:
        return None


# =========================
# TOP 100
# =========================

def get_top_100():

    data = get_json(TICKER_URL)

    content = unwrap_data(data)

    if not isinstance(content, list):
        raise Exception(
            f"Unexpected ticker response: {type(content).__name__}"
        )

    markets = []

    for item in content:

        if not isinstance(item, dict):
            continue

        symbol = (
            item.get("symbol")
            or item.get("contract")
            or item.get("contractName")
            or item.get("instrument")
        )

        if not symbol:
            continue

        # حجم 24 ساعته
        volume = (
            item.get("volume24h")
            or item.get("volume")
            or item.get("vol24h")
            or item.get("turnover24h")
            or item.get("quoteVolume")
        )

        volume = number(volume)

        if volume is None:
            volume = 0

        markets.append({
            "symbol": str(symbol),
            "volume": volume,
            "raw": item
        })

    # مرتب‌سازی بر اساس حجم 24 ساعته
    markets.sort(
        key=lambda x: x["volume"],
        reverse=True
    )

    return markets[:TOP_N]


# =========================
# KLINES
# =========================

def get_klines(symbol):

    params = {
        "symbol": symbol,
        "interval": TIMEFRAME,
        "limit": CANDLE_LIMIT
    }

    data = get_json(
        KLINE_URL,
        params=params
    )

    content = unwrap_data(data)

    if not isinstance(content, list):
        raise Exception(
            f"Unexpected kline response for {symbol}: "
            f"{type(content).__name__}"
        )

    candles = []

    for item in content:

        # حالت استاندارد آرایه‌ای:
        # [timestamp, open, high, low, close, volume]
        if isinstance(item, list) and len(item) >= 6:

            candles.append({
                "time": item[0],
                "open": number(item[1]),
                "high": number(item[2]),
                "low": number(item[3]),
                "close": number(item[4]),
                "volume": number(item[5])
            })

        # حالت object
        elif isinstance(item, dict):

            candles.append({
                "time": (
                    item.get("time")
                    or item.get("timestamp")
                    or item.get("ts")
                ),
                "open": number(item.get("open")),
                "high": number(item.get("high")),
                "low": number(item.get("low")),
                "close": number(item.get("close")),
                "volume": number(
                    item.get("volume")
                    or item.get("vol")
                )
            })

    candles = [
        c for c in candles
        if c["open"] is not None
        and c["high"] is not None
        and c["low"] is not None
        and c["close"] is not None
    ]

    if len(candles) < RSI_PERIOD + 10:
        raise Exception(
            f"Not enough candles for {symbol}: {len(candles)}"
        )

    return candles


# =========================
# RSI 14
# =========================

def calculate_rsi(closes, period=14):

    if len(closes) <= period:
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

    rsi_values = []

    if avg_loss == 0:
        rsi_values.append(100)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(
            100 - (100 / (1 + rs))
        )

    for i in range(period, len(gains)):

        avg_gain = (
            (avg_gain * (period - 1))
            + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1))
            + losses[i]
        ) / period

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        rsi_values.append(rsi)

    return rsi_values


# =========================
# PIVOT
# =========================

def calculate_pivot(candle):

    high = candle["high"]
    low = candle["low"]
    close = candle["close"]

    pivot = (high + low + close) / 3

    support_1 = (2 * pivot) - high
    resistance_1 = (2 * pivot) - low

    support_2 = pivot - (high - low)
    resistance_2 = pivot + (high - low)

    return {
        "pivot": pivot,
        "s1": support_1,
        "s2": support_2,
        "r1": resistance_1,
        "r2": resistance_2
    }


# =========================
# DISTANCE
# =========================

def distance_percent(price, level):

    if level == 0:
        return 999

    return abs(price - level) / level * 100


# =========================
# LOCAL EXTREMA
# =========================

def is_local_low(values, i):

    if i <= 0 or i >= len(values) - 1:
        return False

    return (
        values[i] < values[i - 1]
        and values[i] <= values[i + 1]
    )


def is_local_high(values, i):

    if i <= 0 or i >= len(values) - 1:
        return False

    return (
        values[i] > values[i - 1]
        and values[i] >= values[i + 1]
    )


# =========================
# RSI DIVERGENCE
# =========================

def find_bullish_divergence(closes, rsi):

    if len(rsi) < 10:
        return False

    # آخرین بخش نمودار
    start = max(1, len(closes) - 35)

    lows = []

    for i in range(start, len(closes) - 1):

        # RSI با offset دوره‌ای نسبت به close محاسبه شده
        rsi_index = i - RSI_PERIOD

        if rsi_index < 0 or rsi_index >= len(rsi):
            continue

        if is_local_low(closes, i):
            lows.append(
                (i, closes[i], rsi[rsi_index])
            )

    if len(lows) < 2:
        return False

    first = lows[-2]
    second = lows[-1]

    price_lower_low = second[1] < first[1]
    rsi_higher_low = second[2] > first[2]

    return price_lower_low and rsi_higher_low


def find_bearish_divergence(closes, rsi):

    if len(rsi) < 10:
        return False

    start = max(1, len(closes) - 35)

    highs = []

    for i in range(start, len(closes) - 1):

        rsi_index = i - RSI_PERIOD

        if rsi_index < 0 or rsi_index >= len(rsi):
            continue

        if is_local_high(closes, i):
            highs.append(
                (i, closes[i], rsi[rsi_index])
            )

    if len(highs) < 2:
        return False

    first = highs[-2]
    second = highs[-1]

    price_higher_high = second[1] > first[1]
    rsi_lower_high = second[2] < first[2]

    return price_higher_high and rsi_lower_high


# =========================
# ANALYZE SYMBOL
# =========================

def analyze_symbol(symbol):

    candles = get_klines(symbol)

    closes = [
        c["close"]
        for c in candles
    ]

    rsi_values = calculate_rsi(
        closes,
        RSI_PERIOD
    )

    if not rsi_values:
        return None

    current_price = closes[-1]
    current_rsi = rsi_values[-1]

    # برای Pivot از آخرین کندل بسته‌شده استفاده می‌کنیم
    pivot_candle = candles[-2]

    levels = calculate_pivot(
        pivot_candle
    )

    bullish_divergence = (
        find_bullish_divergence(
            closes,
            rsi_values
        )
    )

    bearish_divergence = (
        find_bearish_divergence(
            closes,
            rsi_values
        )
    )

    support_levels = [
        ("S1", levels["s1"]),
        ("S2", levels["s2"])
    ]

    resistance_levels = [
        ("R1", levels["r1"]),
        ("R2", levels["r2"])
    ]

    near_support = None

    for name, level in support_levels:

        if distance_percent(
            current_price,
            level
        ) <= SR_DISTANCE_PERCENT:

            near_support = (
                name,
                level
            )
            break

    near_resistance = None

    for name, level in resistance_levels:

        if distance_percent(
            current_price,
            level
        ) <= SR_DISTANCE_PERCENT:

            near_resistance = (
                name,
                level
            )
            break

    # هشدار فقط وقتی واگرایی نزدیک حمایت/مقاومت باشد
    if near_support and bullish_divergence:

        return {
            "type": "bullish",
            "symbol": symbol,
            "price": current_price,
            "rsi": current_rsi,
            "level_name": near_support[0],
            "level": near_support[1]
        }

    if near_resistance and bearish_divergence:

        return {
            "type": "bearish",
            "symbol": symbol,
            "price": current_price,
            "rsi": current_rsi,
            "level_name": near_resistance[0],
            "level": near_resistance[1]
        }

    return None


# =========================
# MESSAGE
# =========================

def format_alert(signal):

    if signal["type"] == "bullish":

        title = "🟢 واگرایی مثبت RSI"

        location = "نزدیک حمایت"

    else:

        title = "🔴 واگرایی منفی RSI"

        location = "نزدیک مقاومت"

    return (
        f"{title}\n\n"
        f"💰 ارز: {signal['symbol']}\n"
        f"⏱ تایم‌فریم: 1H\n"
        f"📍 وضعیت: {location}\n\n"
        f"💵 قیمت: {signal['price']:.8g}\n"
        f"📊 RSI(14): {signal['rsi']:.2f}\n"
        f"📐 سطح {signal['level_name']}: "
        f"{signal['level']:.8g}\n\n"
        f"⚠️ فقط هشدار — بدون معامله"
    )


# =========================
# MAIN
# =========================

def main():

    print("🚀 Ourbit Alert Bot Started")

    if not TOKEN:
        raise Exception(
            "TELEGRAM_BOT_TOKEN is missing"
        )

    if not CHAT_ID:
        raise Exception(
            "TELEGRAM_CHAT_ID is missing"
        )

    print("📡 Getting Top 100 Futures...")

    markets = get_top_100()

    print(
        f"📊 Top {len(markets)} markets received"
    )

    if not markets:
        raise Exception(
            "No Futures markets found"
        )

    alerts = 0
    checked = 0

    errors = 0

    for market in markets:

        symbol = market["symbol"]

        try:

            print(
                f"🔍 Checking {symbol}"
            )

            signal = analyze_symbol(
                symbol
            )

            checked += 1

            if signal:

                message = format_alert(
                    signal
                )

                send_telegram(message)

                alerts += 1

                print(
                    f"🚨 ALERT: {symbol}"
                )

            time.sleep(
                SLEEP_BETWEEN_REQUESTS
            )

        except Exception as e:

            errors += 1

            print(
                f"⚠️ {symbol}: {e}"
            )

    print("\n====================")
    print("✅ BOT FINISHED")
    print(
        f"📊 Checked: {checked}"
    )
    print(
        f"🚨 Alerts: {alerts}"
    )
    print(
        f"⚠️ Errors: {errors}"
    )
    print("====================")


# =========================
# RUN
# =========================

if __name__ == "__main__":
    try:

        main()

    except Exception as e:

        error = traceback.format_exc()

        print(error)

        if TOKEN and CHAT_ID:

            try:

                send_telegram(
                    "❌ خطای ربات\n\n"
                    f"{type(e).__name__}: {e}\n\n"
                    f"{error[-2500:]}"
                )

            except Exception:
                pass

        raise
