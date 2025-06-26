from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import requests
import os

app = Flask(__name__)

API_KEY = os.getenv("MEXC_API_KEY")
API_SECRET = os.getenv("MEXC_API_SECRET")
BASE_URL = "https://contract.mexc.com"

SYMBOL = "USELESSUSDT"
LEVERAGE = 50
TP_PERCENT = 0.02
SL_PERCENTAGES = [0.005, 0.0051, 0.0052, 0.0053, 0.0054, 0.0055]

current_position = None

def sign_params(params):
    sorted_params = sorted(params.items())
    query_string = "&".join(f"{key}={value}" for key, value in sorted_params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

def get_headers():
    return {
        "Content-Type": "application/json",
        "ApiKey": API_KEY
    }

def get_balance():
    path = "/api/v1/private/account/assets"
    timestamp = str(int(time.time() * 1000))
    params = {"timestamp": timestamp}
    signature = sign_params(params)
    url = f"{BASE_URL}{path}?timestamp={timestamp}&signature={signature}"
    response = requests.get(url, headers=get_headers())
    data = response.json()
    for item in data.get("data", []):
        if item["currency"] == "USDT":
            return float(item["availableBalance"])
    return 0

def cancel_orders():
    path = "/api/v1/private/order/cancel-all"
    timestamp = str(int(time.time() * 1000))
    params = {"symbol": SYMBOL, "timestamp": timestamp}
    signature = sign_params(params)
    url = f"{BASE_URL}{path}?timestamp={timestamp}&signature={signature}"
    requests.post(url, headers=get_headers(), json=params)

def close_position():
    path = "/api/v1/private/position/close"
    timestamp = str(int(time.time() * 1000))
    params = {"symbol": SYMBOL, "timestamp": timestamp}
    signature = sign_params(params)
    url = f"{BASE_URL}{path}?timestamp={timestamp}&signature={signature}"
    requests.post(url, headers=get_headers(), json=params)

def place_order(side, quantity):
    path = "/api/v1/private/order/submit"
    timestamp = str(int(time.time() * 1000))
    order_type = 1  # Market order
    params = {
        "symbol": SYMBOL,
        "price": 0,
        "vol": quantity,
        "side": 1 if side == "buy" else 2,
        "type": order_type,
        "open_type": 1,
        "position_id": 0,
        "leverage": LEVERAGE,
        "external_oid": str(timestamp),
        "timestamp": timestamp
    }
    signature = sign_params(params)
    url = f"{BASE_URL}{path}?timestamp={timestamp}&signature={signature}"
    return requests.post(url, headers=get_headers(), json=params)

@app.route("/webhook", methods=["POST"])
def webhook():
    global current_position

    signal = request.json.get("signal")
    if not signal or signal not in ["buy", "sell"]:
        return jsonify({"error": "Invalid signal"}), 400

    try:
        print(f"Signal empfangen: {signal}")
        cancel_orders()
        if current_position:
            print("Schließe vorherigen Trade")
            close_position()

        balance = get_balance()
        quantity = round((balance * 0.5 * LEVERAGE), 2)
        print(f"Placing {signal} order with qty: {quantity}")

        result = place_order(signal, quantity)
        print("Order gesetzt:", result.json())

        current_position = signal

        return jsonify({"msg": f"Signal {signal} empfangen", "status": "ok"})

    except Exception as e:
        print("Fehler:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
