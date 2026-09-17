import os
import requests
import pandas as pd

# =========================
# SETTINGS
# =========================

SYMBOL = "ETH_USDT"
INTERVAL = "Min15"
NEAR_PERCENT = 0.3

OURBIT_URL = (
    "https://futures.ourbit.com/"
    "api/v1/contract/kline/ETH_USDT"
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# =========================
# TELEGRAM
# =========================

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram secrets are missing.")
        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    try:
        response = requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            },
            timeout=20
        )

        print("Telegram:", response.status_code)
        print(response.text)

        return response.ok

    except Exception as e:
        print("Telegram error:", e)
        return False


# =========================
# OURBIT KLINES
# =========================

def get_klines():
    print("========== OURBIT REQUEST ==========")
    print("URL:", OURBIT_URL)
    print("Symbol:", SYMBOL)
    print("Interval:", INTERVAL)

    try:
        response = requests.get(
            OURBIT_URL,
            params={"interval": INTERVAL},
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
# CONVERT DATA
# =========================

def make_dataframe(data):

    if not data:
        return None

    try:
        # تلاش برای تشخیص ساختار Kline
        rows = data

        if isinstance(data, dict):
            for key in ["list", "rows", "data", "result"]:
                if key in data:
                    rows = data[key]
                    break

        if not isinstance(rows, list):
            print("Unexpected kline format:", type(rows))
            return None

        if len(rows) == 0:
            print("No kline data.")
            return None

        df = pd.DataFrame(rows)

        print("Kline rows:", len(df))
        print("Columns:", list(df.columns))

        return df

    except Exception as e:
        print("Data conversion error:", e)
        return None


# =========================
# FIND PRICE
# =========================

def get_current_price(df):

    possible_columns = [
        "close",
        "Close",
        "c",
        4
    ]

    for column in possible_columns:
        if column in df.columns:
            try:
                return float(df[column].iloc[-1])
            except:
                pass

    # اگر داده به صورت آرایه‌ای باشد
    try:
        if len(df.columns) >= 5:
            return float(df.iloc[-1, 4])
    except:
        pass

    return None


# =========================
# SUPPORT / RESISTANCE
# =========================

def calculate_support_resistance(df):

    if df is None or len(df) < 20:
        return None, None

    try:
        high_col = None
        low_col = None

        for col in ["high", "High", "h", 2]:
            if col in df.columns:
                high_col = col
                break

        for col in ["low", "Low", "l", 3]:
            if col in df.columns:
                low_col = col
                break

        if high_col is None or low_col is None:
            print("High/Low columns not found.")
            return None, None

        highs = pd.to_numeric(df[high_col], errors="coerce")
        lows = pd.to_numeric(df[low_col], errors="coerce")

        resistance = highs.tail(20).max()
        support = lows.tail(20).min()

        return float(support), float(resistance)

    except Exception as e:
        print("Support/Resistance error:", e)
        return None, None


# =========================
# ALERT CHECK
# =========================

def check_alert(price, support, resistance):

    if price is None or support is None or resistance is None:
        return None

    support_distance = abs(price - support) / support * 100
    resistance_distance = abs(price - resistance) / resistance * 100

    if support_distance <= NEAR_PERCENT:
        return (
            "🟢 نزدیک حمایت\n\n"
            f"ارز: ETH/USDT\n"
            f"قیمت: {price}\n"
            f"حمایت: {support:.4f}\n"
            f"فاصله: {support_distance:.3f}%"
        )

    if resistance_distance <= NEAR_PERCENT:
        return (
            "🔴 نزدیک مقاومت\n\n"
            f"ارز: ETH/USDT\n"
            f"قیمت: {price}\n"
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

    price = get_current_price(df)

    if price is None:
        raise ValueError("Could not find current price")

    support, resistance = calculate_support_resistance(df)

    if support is None or resistance is None:
        raise ValueError("Could not calculate Support/Resistance")

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
