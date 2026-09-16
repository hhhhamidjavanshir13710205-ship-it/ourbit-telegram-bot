import os
import time
import requests

OURBIT_URL = "https://contract.ourbit.com"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TOP_SYMBOLS = 100
KLINE_LIMIT = 120
RSI_PERIOD = 14

# درصد نزدیکی قیمت به حمایت/مقاومت
LEVEL_DISTANCE = 0.006


def get_json(url, params=None):
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and data.get("code") not in (None, 200):
        raise RuntimeError(f"Ourbit error: {data}")

    return data


def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram secrets are missing.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        },
        timeout=20
    )

    response.raise_for_status()


def get_tickers():
    data = get_json(
        f"{OURBIT_URL}/api/v1/contract/ticker"
    )

    if isinstance(data, dict):
        data = data.get("data", [])

    return data


def get_top_symbols():
    tickers = get_tickers()

    valid = []

    for item in tickers:
        try:
            symbol = item["symbol"]
            volume = float(item.get("volume", 0))
            last = float(item.get("last", 0))

            if last > 0:
                valid.append({
                    "symbol": symbol,
                    "volume": volume,
                    "last": last
                })
        except Exception:
            continue

    valid.sort(
        key=lambda x: x["volume"],
        reverse=True
    )

    return valid[:TOP_SYMBOLS]


def get_klines(symbol):
    data = get_json(
        f"{OURBIT_URL}/api/v1/contract/kline/{symbol}",
        params={
            "interval": "Min60",
            "limit": KLINE_LIMIT
        }
    )

    if isinstance(data, dict):
        data = data.get("data", [])

    candles = []

    for row in data:
        try:
            # Ourbit Kline format:
            # time, open, close, high, low, volume, amount
            candles.append({
                "time": float(row[0]),
                "open": float(row[1]),
                "close": float(row[2]),
                "high": float(row[3]),
                "low": float(row[4]),
                "volume": float(row[5])
            })
        except Exception:
            continue

    return candles


def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]

        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (
            (avg_gain * (period - 1)) + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1)) + losses[i]
        ) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def find_pivots(candles):
    lows = []
    highs = []

    for i in range(2, len(candles) - 2):

        low = candles[i]["low"]
        high = candles[i]["high"]

        if (
            low < candles[i - 1]["low"]
            and low < candles[i - 2]["low"]
            and low < candles[i + 1]["low"]
            and low < candles[i + 2]["low"]
        ):
            lows.append(low)

        if (
            high > candles[i - 1]["high"]
            and high > candles[i - 2]["high"]
            and high > candles[i + 1]["high"]
            and high > candles[i + 2]["high"]
        ):
            highs.append(high)

    return lows, highs


def nearest_level(price, levels):
    if not levels:
        return None

    return min(
        levels,
        key=lambda x: abs(x - price)
    )


def near_level(price, level):
    if level is None or level == 0:
        return False

    return abs(price - level) / level <= LEVEL_DISTANCE


def detect_divergence(candles):
    if len(candles) < 40:
        return None

    closes = [x["close"] for x in candles]

    # RSI series
    rsi_values = []

    for i in range(RSI_PERIOD, len(closes)):
        rsi = calculate_rsi(
            closes[:i + 1],
            RSI_PERIOD
        )

        if rsi is not None:
            rsi_values.append((i, rsi))

    if len(rsi_values) < 10:
        return None

    # فقط بخش پایانی بازار را بررسی می‌کنیم
    recent_start = max(
        RSI_PERIOD,
        len(candles) - 45
    )

    lows = []
    highs = []

    for i in range(
        recent_start + 2,
        len(candles) - 2
    ):
        if (
            candles[i]["low"] < candles[i - 1]["low"]
            and candles[i]["low"] < candles[i - 2]["low"]
            and candles[i]["low"] < candles[i + 1]["low"]
            and candles[i]["low"] < candles[i + 2]["low"]
        ):
            lows.append(i)

        if (
            candles[i]["high"] > candles[i - 1]["high"]
            and candles[i]["high"] > candles[i - 2]["high"]
            and candles[i]["high"] > candles[i + 1]["high"]
            and candles[i]["high"] > candles[i + 2]["high"]
        ):
            highs.append(i)

    # واگرایی صعودی
    if len(lows) >= 2:
        i1, i2 = lows[-2], lows[-1]

        rsi1 = calculate_rsi(
            closes[:i1 + 1],
            RSI_PERIOD
        )

        rsi2 = calculate_rsi(
            closes[:i2 + 1],
            RSI_PERIOD
        )

        if (
            rsi1 is not None
            and rsi2 is not None
            and candles[i2]["low"] < candles[i1]["low"]
            and rsi2 > rsi1
        ):
            return "bullish"

    # واگرایی نزولی
    if len(highs) >= 2:
        i1, i2 = highs[-2], highs[-1]

        rsi1 = calculate_rsi(
            closes[:i1 + 1],
            RSI_PERIOD
        )

        rsi2 = calculate_rsi(
            closes[:i2 + 1],
            RSI_PERIOD
        )

        if (
            rsi1 is not None
            and rsi2 is not None
            and candles[i2]["high"] > candles[i1]["high"]
            and rsi2 < rsi1
        ):
            return "bearish"

    return None


def analyze_symbol(symbol):
    candles = get_klines(symbol)

    if len(candles) < 50:
        return None

    # آخرین کندل کامل
    candles = candles[:-1]

    price = candles[-1]["close"]

    lows, highs = find_pivots(candles)

    support = nearest_level(price, lows)
    resistance = nearest_level(price, highs)

    alerts = []

    if support and near_level(price, support):
        alerts.append(
            f"🟢 نزدیک حمایت\n"
            f"حمایت: {support:.8g}\n"
            f"قیمت: {price:.8g}"
        )

    if resistance and near_level(price, resistance):
        alerts.append(
            f"🔴 نزدیک مقاومت\n"
            f"مقاومت: {resistance:.8g}\n"
            f"قیمت: {price:.8g}"
        )

    divergence = detect_divergence(candles)

    if divergence == "bullish" and support and near_level(price, support):
        alerts.append(
            "📈 واگرایی صعودی RSI نزدیک حمایت"
        )

    if divergence == "bearish" and resistance and near_level(price, resistance):
        alerts.append(
            "📉 واگرایی نزولی RSI نزدیک مقاومت"
        )

    if not alerts:
        return None

    rsi = calculate_rsi(
        [x["close"] for x in candles],
        RSI_PERIOD
    )

    return (
        f"⚡ هشدار Futures - 1H\n\n"
        f"📌 {symbol}\n"
        f"💰 قیمت: {price:.8g}\n"
        f"📊 RSI(14): {rsi:.2f}\n\n"
        + "\n\n".join(alerts)
    )


def main():
    print("Starting Ourbit Futures scanner...")

    symbols = get_top_symbols()

    print(
        f"Found {len(symbols)} top Futures contracts."
    )

    sent = 0

    for item in symbols:
        symbol = item["symbol"]

        try:
            alert = analyze_symbol(symbol)

            if alert:
                send_telegram(alert)
                sent += 1

            print(f"Checked {symbol}")

        except Exception as e:
            print(
                f"Error checking {symbol}: {e}"
            )

    print(
        f"Finished. Alerts sent: {sent}"
    )


if __name__ == "__main__":
    main()
