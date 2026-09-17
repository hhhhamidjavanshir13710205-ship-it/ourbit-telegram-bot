import os
import time
import requests

# =========================================================
# Telegram
# =========================================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =========================================================
# Settings
# =========================================================

SYMBOL = "ETH_USDT"
INTERVAL = "Min15"

CANDLE_LIMIT = 150

# فاصله مجاز قیمت از حمایت/مقاومت
NEAR_PERCENT = 0.30

# قدرت Pivot
PIVOT_STRENGTH = 3

# =========================================================
# Ourbit API
# =========================================================

API_URL = (
    f"https://contract.ourbit.com"
    f"/api/v1/contract/kline/{SYMBOL}"
)


# =========================================================
# Telegram message
# =========================================================

def send_telegram(message):

    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is missing")
        return False

    if not CHAT_ID:
        print("ERROR: TELEGRAM_CHAT_ID is missing")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        print("Telegram:", response.status_code)
        print(response.text)

        return response.ok

    except Exception as e:

        print("Telegram error:", e)

        return False


# =========================================================
# Get candles from Ourbit
# =========================================================

def get_candles():

    now_ms = int(time.time() * 1000)

    # 15 دقیقه برای هر کندل
    candle_duration_ms = 15 * 60 * 1000

    start_ms = now_ms - (
        CANDLE_LIMIT * candle_duration_ms
    )

    params = {
        "interval": INTERVAL,
        "start": start_ms,
        "end": now_ms
    }

    print()
    print("========== OURBIT REQUEST ==========")
    print("URL:", API_URL)
    print("Symbol:", SYMBOL)
    print("Interval:", INTERVAL)
    print("Start:", start_ms)
    print("End:", now_ms)
    print("====================================")

    try:

        response = requests.get(
            API_URL,
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=30
        )

        print("Ourbit HTTP:", response.status_code)

        response.raise_for_status()

        data = response.json()

        print()
        print("========== OURBIT RESPONSE ==========")
        print(data)
        print("======================================")

        return data

    except Exception as e:

        print("Ourbit request error:", e)

        return None


# =========================================================
# Parse candles
# =========================================================

def parse_candles(response):

    if response is None:

        raise ValueError(
            "Ourbit response is None"
        )

    if not isinstance(response, dict):

        raise ValueError(
            "Unexpected Ourbit response type"
        )

    if response.get("success") is False:

        raise ValueError(
            f"Ourbit error: "
            f"{response.get('code')} - "
            f"{response.get('message')}"
        )

    data = response.get("data")

    if not data:

        raise ValueError(
            "Candle data is empty"
        )

    # -----------------------------------------------------
    # Official Ourbit/MEXC-style contract Kline structure:
    #
    # data = {
    #   "time": [...],
    #   "open": [...],
    #   "close": [...],
    #   "high": [...],
    #   "low": [...],
    #   "vol": [...],
    #   "amount": [...]
    # }
    # -----------------------------------------------------

    if isinstance(data, dict):

        times = data.get("time", [])
        opens = data.get("open", [])
        closes = data.get("close", [])
        highs = data.get("high", [])
        lows = data.get("low", [])

        if not times:
            raise ValueError(
                "Ourbit returned no candle times"
            )

        length = min(
            len(times),
            len(opens),
            len(closes),
            len(highs),
            len(lows)
        )

        candles = []

        for i in range(length):

            candles.append({
                "time": float(times[i]),
                "open": float(opens[i]),
                "high": float(highs[i]),
                "low": float(lows[i]),
                "close": float(closes[i])
            })

        candles.sort(
            key=lambda x: x["time"]
        )

        print()
        print("Parsed candles:", len(candles))

        if candles:

            print(
                "First candle:",
                candles[0]
            )

            print(
                "Last candle:",
                candles[-1]
            )

        return candles

    # -----------------------------------------------------
    # Backup parser in case API returns list
    # -----------------------------------------------------

    if isinstance(data, list):

        candles = []

        for item in data:

            if isinstance(item, dict):

                try:

                    candle = {
                        "time": float(
                            item.get("time", item.get("t"))
                        ),
                        "open": float(
                            item.get("open", item.get("o"))
                        ),
                        "high": float(
                            item.get("high", item.get("h"))
                        ),
                        "low": float(
                            item.get("low", item.get("l"))
                        ),
                        "close": float(
                            item.get("close", item.get("c"))
                        )
                    }

                    candles.append(candle)

                except Exception:
                    continue

            elif isinstance(item, list):

                # Backup for row-style candle data
                if len(item) >= 6:

                    try:

                        candles.append({
                            "time": float(item[0]),
                            "open": float(item[1]),
                            "high": float(item[2]),
                            "low": float(item[3]),
                            "close": float(item[4])
                        })

                    except Exception:
                        continue

        candles.sort(
            key=lambda x: x["time"]
        )

        print(
            "Parsed list candles:",
            len(candles)
        )

        return candles

    raise ValueError(
        "Unknown Ourbit candle structure"
    )


# =========================================================
# Pivot detection
# =========================================================

def find_pivots(candles, strength=3):

    supports = []
    resistances = []

    total = len(candles)

    if total < (strength * 2 + 1):

        return supports, resistances

    for i in range(
        strength,
        total - strength
    ):

        current = candles[i]

        current_low = current["low"]
        current_high = current["high"]

        is_support = True
        is_resistance = True

        # -----------------------------------------------
        # Check candles around pivot
        # -----------------------------------------------

        for j in range(
            i - strength,
            i + strength + 1
        ):

            if j == i:
                continue

            if candles[j]["low"] <= current_low:
                is_support = False

            if candles[j]["high"] >= current_high:
                is_resistance = False

        if is_support:

            supports.append({
                "price": current_low,
                "time": current["time"]
            })

        if is_resistance:

            resistances.append({
                "price": current_high,
                "time": current["time"]
            })

    return supports, resistances


# =========================================================
# Merge nearby levels
# =========================================================

def merge_levels(levels):

    if not levels:

        return []

    levels = sorted(
        levels,
        key=lambda x: x["price"]
    )

    merged = []

    for level in levels:

        if not merged:

            merged.append(level)

            continue

        last = merged[-1]

        distance_percent = (
            abs(
                level["price"] -
                last["price"]
            )
            / last["price"]
        ) * 100

        if distance_percent <= NEAR_PERCENT:

            # میانگین دو سطح
            last["price"] = (
                last["price"] +
                level["price"]
            ) / 2

        else:

            merged.append(level)

    return merged


# =========================================================
# Find nearest level
# =========================================================

def find_nearest_support(
    price,
    supports
):

    below = [
        x for x in supports
        if x["price"] <= price
    ]

    if not below:
        return None

    return max(
        below,
        key=lambda x: x["price"]
    )


def find_nearest_resistance(
    price,
    resistances
):

    above = [
        x for x in resistances
        if x["price"] >= price
    ]

    if not above:
        return None

    return min(
        above,
        key=lambda x: x["price"]
    )


# =========================================================
# Check distance
# =========================================================

def distance_percent(price, level):

    return (
        abs(price - level)
        / level
    ) * 100


# =========================================================
# Analyze market
# =========================================================

def analyze(candles):

    if len(candles) < 20:

        print(
            "Not enough candles"
        )

        return None

    # -----------------------------------------------------
    # آخرین کندل ممکن است هنوز در حال تشکیل باشد.
    # از آخرین کندل بسته‌شده استفاده می‌کنیم.
    # -----------------------------------------------------

    closed_candle = candles[-2]

    price = closed_candle["close"]

    print()
    print("========== MARKET ==========")
    print(
        "Closed candle price:",
        price
    )
    print("=============================")

    # -----------------------------------------------------
    # Find pivots
    # -----------------------------------------------------

    supports, resistances = find_pivots(
        candles,
        PIVOT_STRENGTH
    )

    # -----------------------------------------------------
    # Merge nearby levels
    # -----------------------------------------------------

    supports = merge_levels(
        supports
    )

    resistances = merge_levels(
        resistances
    )

    print()
    print("========== LEVELS ==========")

    print("Supports:")

    for level in supports:

        print(
            round(level["price"], 4)
        )

    print("Resistances:")

    for level in resistances:

        print(
            round(level["price"], 4)
        )

    print("============================")

    # -----------------------------------------------------
    # Nearest support
    # -----------------------------------------------------

    support = find_nearest_support(
        price,
        supports
    )

    # -----------------------------------------------------
    # Nearest resistance
    # -----------------------------------------------------

    resistance = find_nearest_resistance(
        price,
        resistances
    )

    # -----------------------------------------------------
    # Support signal
    # -----------------------------------------------------

    if support:

        support_distance = distance_percent(
            price,
            support["price"]
        )

        print()
        print(
            "Nearest support:",
            support["price"]
        )

        print(
            "Support distance:",
            round(
                support_distance,
                4
            ),
            "%"
        )

        if support_distance <= NEAR_PERCENT:

            return {
                "type": "SUPPORT",
                "price": price,
                "level": support["price"],
                "distance": support_distance
            }

    # -----------------------------------------------------
    # Resistance signal
    # -----------------------------------------------------

    if resistance:

        resistance_distance = distance_percent(
            price,
            resistance["price"]
        )

        print()
        print(
            "Nearest resistance:",
            resistance["price"]
        )

        print(
            "Resistance distance:",
            round(
                resistance_distance,
                4
            ),
            "%"
        )

        if resistance_distance <= NEAR_PERCENT:

            return {
                "type": "RESISTANCE",
                "price": price,
                "level": resistance["price"],
                "distance": resistance_distance
            }

    return None


# =========================================================
# Create Telegram signal
# =========================================================

def create_message(signal):

    if signal["type"] == "SUPPORT":

        return (
            "🟢 ETHUSDT — SUPPORT\n\n"
            f"💰 Price: {signal['price']:.2f}\n"
            f"🟢 Support: {signal['level']:.2f}\n"
            f"📏 Distance: {signal['distance']:.2f}%\n\n"
            "⏱ Timeframe: 15M\n"
            "📊 Dynamic Support/Resistance"
        )

    if signal["type"] == "RESISTANCE":

        return (
            "🔴 ETHUSDT — RESISTANCE\n\n"
            f"💰 Price: {signal['price']:.2f}\n"
            f"🔴 Resistance: {signal['level']:.2f}\n"
            f"📏 Distance: {signal['distance']:.2f}%\n\n"
            "⏱ Timeframe: 15M\n"
            "📊 Dynamic Support/Resistance"
        )

    return "No signal"


# =========================================================
# Main
# =========================================================

def main():

    print()
    print("================================")
    print("Starting SR Dynamic V2 Bot")
    print("Symbol:", SYMBOL)
    print("Timeframe:", INTERVAL)
    print("Near:", NEAR_PERCENT, "%")
    print("================================")

    try:

        # Get data
        data = get_candles()

        # Parse
        candles = parse_candles(
            data
        )

        if len(candles) < 20:

            raise ValueError(
                "Not enough candle data"
            )

        # Analyze
        signal = analyze(
            candles
        )

        # -------------------------------------------------
        # Signal found
        # -------------------------------------------------

        if signal:

            message = create_message(
                signal
            )

            print()
            print("========== SIGNAL ==========")
            print(message)
            print("============================")

            send_telegram(
                message
            )

        else:

            print()
            print("================================")
            print("No signal")
            print("Price is not near support/resistance")
            print("================================")

    except Exception as e:

        print()
        print("========== ERROR ==========")
        print(type(e).__name__)
        print(str(e))
        print("============================")

        raise


# =========================================================
# Run
# =========================================================

if __name__ == "__main__":

    main()
