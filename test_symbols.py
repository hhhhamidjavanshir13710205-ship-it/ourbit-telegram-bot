import requests

URL = "https://futures.ourbit.com/api/v1/contract/ticker"

try:
    response = requests.get(URL, timeout=30)

    print("HTTP:", response.status_code)
    print("RESPONSE:")
    print(response.text[:5000])

except Exception as e:
    print("ERROR:", e)
