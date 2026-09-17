import os
import requests

# =========================
# SETTINGS
# =========================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOL = "ETHUSDT"
INTERVAL = "15m"

CANDLE_LIMIT = 100

# فاصله مجاز قیمت از حمایت/مقاومت
NEAR_PERCENT = 0.30

API_URL = (
    f"https://futures.ourbit.com/api/v1/contract/kline/"
    f"{SYMBOL}?interval={INTERVAL}&limit={CANDLE_LIMIT}"
)

TELEGRAM_URL = (
    f"https://api.telegram.org/bot{TOKEN}/sendMessage"
)


# =========================
# TELEGRAM
# =========================

def send_telegram(message):

    response = requests.post(
        TELEGRAM_URL,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    print("Telegram:", response.status_code)
    print(response.text)

    return response


# =========================
# GET CANDLES
# =========================

def get_candles():

    response = requests.get(
        API_URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    print("Ourbit:", response.status_code)

    response.raise_for_status()

    data = response.json()

    print("Ourbit response type:", type(data))

    return data


# =========================
# PARSE CANDLES
# =========================

def parse_candles(data):

    raw = None

    # -------------------------
    # Dictionary response
    # -------------------------

    if isinstance(data, dict):

        raw = data.get("data")

        if raw is None:
            raw = data.get("result")

        if raw is None:
            raw = data.get("rows")

        # بعضی API ها داده را داخل result/data تو در تو می‌گذارند
        if isinstance(raw, dict):

            raw = (
                raw.get("data")
                or raw.get("rows")
                or raw.get("list")
                or raw.get("result")
            )

    # -------------------------
    # Direct list response
    # -------------------------

    elif isinstance(data, list):

        raw = data

    # -------------------------
    # Empty response
    # -------------------------

    if not raw:

        print("========== DEBUG RESPONSE ==========")
        print(data)
        print("====================================")

        raise ValueError(
            "Candle data is empty"
        )

    candles = []

    # =========================
    # PARSE EACH CANDLE
    # =========================

    for c in raw:

        try:

            # ---------------------
            # Array format
            # ---------------------

            if isinstance(c, list):

                if len(c) < 5:
                    continue

                timestamp = float(c[0])
                open_price = float(c[1])
                high = float(c[2])
                low = float(c[3])
                close = float(c[4])

            # ---------------------
            # Dictionary format
            # ---------------------

            elif isinstance(c, dict):

                timestamp = float(
                    c.get(
                        "timestamp",
                        c.get(
                            "time",
                            c.get(
                                "ts",
                                c.get("t", 0)
                            )
                        )
                    )
                )

                open_price = float(
                    c.get(
                        "open",
                        c.get("o")
                    )
                )

                high = float(
                    c.get(
                        "high",
                        c.get("h")
                    )
                )

                low = float(
                    c.get(
                        "low",
                        c.get("l")
                    )
                )

                close = float(
                    c.get(
                        "close",
                        c.get("c")
                    )
                )

            else:

                continue

            candles.append({
                "time": timestamp,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close
            })

        except Exception as e:

            print(
                "Candle parse error:",
                e
            )

            continue

    # =========================
    # CHECK RESULT
    # =========================

    print(
        "Parsed candles:",
        len(candles)
    )

    if len(candles) < 20:

        print(
            "Raw candle data:"
        )

        print(raw)

        raise ValueError(
            f"Not enough candles: {len(candles)}"
        )

    candles.sort(
        key=lambda x: x["time"]
    )

    return candles


# =========================
# FIND PIVOTS
# =========================

def find_pivots(
    candles,
    strength=3
):

    supports = []
    resistances = []

    for i in range(
        strength,
        len(candles) - strength
    ):

        current = candles[i]

        left = candles[
            i - strength:i
        ]

        right = candles[
            i + 1:i + strength + 1
        ]

        # -------------------------
        # Pivot Low = Support
        # -------------------------

        if all(
            current["low"] <= x["low"]
            for x in left + right
        ):

            supports.append(
                current["low"]
            )

        # -------------------------
        # Pivot High = Resistance
        # -------------------------

        if all(
            current["high"] >= x["high"]
            for x in left + right
        ):

            resistances.append(
                current["high"]
            )

    return supports, resistances


# =========================
# MERGE LEVELS
# =========================

def merge_levels(
    levels,
    tolerance=0.003
):

    if not levels:
        return []

    levels = sorted(levels)

    merged = []

    current = [levels[0]]

    for level in levels[1:]:

        average = (
            sum(current)
            / len(current)
        )

        if (
            abs(level - average)
            / average
            <= tolerance
        ):

            current.append(level)

        else:

            merged.append(
                sum(current)
                / len(current)
            )

            current = [level]

    merged.append(
        sum(current)
        / len(current)
    )

    return merged


# =========================
# NEAREST LEVEL
# =========================

def nearest_level(
    price,
    levels
):

    if not levels:
        return None

    return min(
        levels,
        key=lambda x:
        abs(x - price)
    )


# =========================
# CHECK SIGNAL
# =========================

def check_signal(
    price,
    supports,
    resistances
):

    support = nearest_level(
        price,
        supports
    )

    resistance = nearest_level(
        price,
        resistances
    )

    support_signal = False
    resistance_signal = False

    # -------------------------
    # Support
    # -------------------------

    if support is not None:

        distance = (
            abs(price - support)
            / price
            * 100
        )

        print(
            f"Support distance: "
            f"{distance:.4f}%"
        )

        if (
            support < price
            and distance <= NEAR_PERCENT
        ):

            support_signal = True

    # -------------------------
    # Resistance
    # -------------------------

    if resistance is not None:

        distance = (
            abs(price - resistance)
            / price
            * 100
        )

        print(
            f"Resistance distance: "
            f"{distance:.4f}%"
        )

        if (
            resistance > price
            and distance <= NEAR_PERCENT
        ):

            resistance_signal = True

    return (
        support_signal,
        resistance_signal,
        support,
        resistance
    )


# =========================
# MAIN
# =========================

def main():

    print(
        "================================"
    )

    print(
        "Starting SR Dynamic V2 Bot"
    )

    print(
        f"Symbol: {SYMBOL}"
    )

    print(
        f"Timeframe: {INTERVAL}"
    )

    print(
        "================================"
    )

    # =========================
    # GET DATA
    # =========================

    data = get_candles()

    # =========================
    # PARSE
    # =========================

    candles = parse_candles(data)

    # =========================
    # LAST CLOSED CANDLE
    # =========================

    closed = candles[-2]

    price = closed["close"]

    print(
        f"Price: {price:.4f}"
    )

    # =========================
    # FIND LEVELS
    # =========================

    supports, resistances = find_pivots(
        candles,
        strength=3
    )

    # =========================
    # MERGE LEVELS
    # =========================

    supports = merge_levels(
        supports
    )

    resistances = merge_levels(
        resistances
    )

    print(
        "Supports:",
        supports
    )

    print(
        "Resistances:",
        resistances
    )

    # =========================
    # SIGNAL
    # =========================

    (
        near_support,
        near_resistance,
        support,
        resistance
    ) = check_signal(
        price,
        supports,
        resistances
    )

    # =========================
    # SUPPORT ALERT
    # =========================

    if near_support:

        distance = (
            abs(price - support)
            / price
            * 100
        )

        message = (
            "🟢🔔 ETHUSDT 15M\n\n"
            "📍 نزدیک حمایت\n\n"
            f"💰 قیمت: {price:.4f}\n"
            f"🟢 حمایت: {support:.4f}\n"
            f"📏 فاصله: {distance:.2f}%\n\n"
            "⚠️ قیمت به محدوده حمایت "
            "نزدیک شده است."
        )

        send_telegram(message)

    # =========================
    # RESISTANCE ALERT
    # =========================

    elif near_resistance:

        distance = (
            abs(price - resistance)
            / price
            * 100
        )

        message = (
            "🔴🔔 ETHUSDT 15M\n\n"
            "📍 نزدیک مقاومت\n\n"
            f"💰 قیمت: {price:.4f}\n"
            f"🔴 مقاومت: {resistance:.4f}\n"
            f"📏 فاصله: {distance:.2f}%\n\n"
            "⚠️ قیمت به محدوده مقاومت "
            "نزدیک شده است."
        )

        send_telegram(message)

    # =========================
    # NO SIGNAL
    # =========================

    else:

        print(
            "No signal: price is not near "
            "support or resistance."
        )


# =========================
# START
# =========================

if __name__ == "__main__":

    main()
