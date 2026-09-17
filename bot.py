import os
import requests
import pandas as pd

# =========================
# SETTINGS
# =========================

SYMBOL = "ETH_USDT"
INTERVAL = "Min15"
NEAR_PERCENT = 0.5

OURBIT_URL = "https://futures.ourbit.com/api/v1/contract/kline/ETH_USDT"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# =========================
# TELEGRAM
# =========================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram secrets are missing.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            },
            timeout=20
        )

        print("Telegram status:", response.status_code)
        print("Telegram response:", response.text)

        return response.ok

    except Exception as e:
        print("Telegram error:", e)
        return False


# =========================
# OURBIT KLINE
# =========================

def get_klines():

    print("========== OURBIT REQUEST ==========")
    print("URL:", OURBIT_URL)
    print("Symbol:", SYMBOL)
    print("Interval:", INTERVAL)

    try:

        response = requests.get(
            OURBIT_URL,
            params={
                "interval": INTERVAL
            },
            timeout=30
        )

        print("HTTP STATUS:", response.status_code)
        print("RESPONSE:", response.text[:1000])

        response.raise_for_status()

        result = response.json()

        if not result.get("success"):
            print("Ourbit API returned an error.")
            return None

        return result.get("data")

    except Exception as e:

        print("Ourbit request error:", e)
        return None


# =========================
# CONVERT OURBIT DATA
# =========================

def make_dataframe(data):

    if not data:
        print("Empty Ourbit data.")
        return None

    try:

        # Ourbit returns:
        #
        # {
        #   "time": [...],
        #   "open": [...],
        #   "high": [...],
        #   "low": [...],
        #   "close": [...],
        #   ...
        # }

        if not isinstance(data, dict):
            print("Unexpected data type:", type(data))
            return None

        print("Ourbit data keys:", list(data.keys()))

        # Find OHLC fields
        time_data = data.get("time")
        open_data = data.get("open")
        high_data = data.get("high")
        low_data = data.get("low")
        close_data = data.get("close")

        if not all([
            time_data,
            open_data,
            high_data,
            low_data,
            close_data
        ]):
            print("Missing OHLC data.")
            return None

        length = min(
            len(time_data),
            len(open_data),
            len(high_data),
            len(low_data),
            len(close_data)
        )

        if length == 0:
            print("No candles found.")
            return None

        df = pd.DataFrame({
            "time": time_data[:length],
            "open": open_data[:length],
            "high": high_data[:length],
            "low": low_data[:length],
            "close": close_data[:length]
        })

        df["open"] = pd.to_numeric(df["open"], errors="coerce")
        df["high"] = pd.to_numeric(df["high"], errors="coerce")
        df["low"] = pd.to_numeric(df["low"], errors="coerce")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")

        df = df.dropna(
            subset=[
                "open",
                "high",
                "low",
                "close"
            ]
        )

        print("Kline rows:", len(df))

        return df

    except Exception as e:

        print("Data conversion error:", e)
        return None


# =========================
# SUPPORT / RESISTANCE
# =========================

def calculate_support_resistance(df):

    if df is None or len(df) < 20:
        print("Not enough candles.")
        return None, None

    try:

        recent = df.tail(20)

        support = recent["low"].min()
        resistance = recent["high"].max()

        return float(support), float(resistance)

    except Exception as e:

        print("Support/Resistance error:", e)
        return None, None


# =========================
# ALERT
# =========================

def check_alert(price, support, resistance):

    if price is None:
        return None

    if support is None or resistance is None:
        return None

    support_distance = (
        abs(price - support) / support
    ) * 100

    resistance_distance = (
        abs(price - resistance) / resistance
    ) * 100

    print("Support distance:", support_distance, "%")
    print("Resistance distance:", resistance_distance, "%")

    if support_distance <= NEAR_PERCENT:

        return (
            "🟢 هشدار نزدیک حمایت\n\n"
            "ارز: ETH/USDT\n"
            f"قیمت: {price:.4f}\n"
            f"حمایت: {support:.4f}\n"
            f"فاصله: {support_distance:.3f}%"
        )

    if resistance_distance <= NEAR_PERCENT:

        return (
            "🔴 هشدار نزدیک مقاومت\n\n"
            "ارز: ETH/USDT\n"
            f"قیمت: {price:.4f}\n"
            f"مقاومت: {resistance:.4f}\n"
            f"فاصله: {resistance_distance:.3f}%"
        )

    return None


# =========================
# MAIN
# =========================

def main():

    print()
    print("====================================")
    print("Starting Ourbit Crypto Bot")
    print("Symbol:", SYMBOL)
    print("Timeframe:", INTERVAL)
    print("Near:", NEAR_PERCENT, "%")
    print("====================================")

    data = get_klines()

    if data is None:
        raise ValueError("Ourbit response is None")

    df = make_dataframe(data)

    if df is None:
        raise ValueError("Could not create dataframe")

    print()
    print("========== LAST CANDLE ==========")
    print(df.tail(1).to_string(index=False))
    print("=================================")

    price = float(df["close"].iloc[-1])

    support, resistance = calculate_support_resistance(df)

    if support is None or resistance is None:
        raise ValueError(
            "Could not calculate Support/Resistance"
        )

    print()
    print("========== MARKET ==========")
    print("Price:", price)
    print("Support:", support)
    print("Resistance:", resistance)
    print("============================")

    alert = check_alert(
        price,
        support,
        resistance
    )

    if alert:

        print()
        print("========== ALERT ==========")
        print(alert)
        print("===========================")

        send_telegram(alert)

    else:

        print()
        print("No alert at this time.")


if __name__ == "__main__":
    main()
