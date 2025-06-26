import os
import json
import time
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
BASE_URL = "https://contract.mexc.com"

symbol = "USELESSUSDT"
leverage = 50
tp_percent = 0.02
sl_levels = [0.005, 0.0051, 0.0052, 0.0053, 0.0054, 0.0055]
current_position = None  # "long", "short", or None


def sign_request(req_time, params):
    query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
    to_sign = f"{API_KEY}{req_time}{query_string}"
    signature = hmac.new(API_SECRET.encode(), to_sign.encode(), hashlib.sha256).hexdigest()
    return signature


def get_headers(params={}):
    req_time = str(int(time.time() * 1000))
    signature = sign_request(req_time, params)
    return {
        "ApiKey": API_KEY,
        "Request-Time": req_time,
        "Signature": signature,
        "Content-Type": "application/json"
    }


def get_balance():
    url = f"{BASE_URL}/api/v1/private/account/assets"
    headers = get_headers()
    resp = requests.get(url, headers=headers).json()
    for asset in resp.get("data", []):
        if asset["currency"] == "USDT":
            return float(asset["availableBalance"])
    return 0.0


def cancel_all_orders():
    url = f"{BASE_URL}/api/v1/private/order/cancel-all"
    data = {"symbol": symbol}
    headers = get_headers(data)
    requests.post(url, headers=headers, data=json.dumps(data))


def close_position():
    global current_position
    if not current_position:
        return
    side = "SELL" if current_position == "long" else "BUY"
    url = f"{BASE_URL}/api/v1/private/order/close-position"
    data = {"symbol": symbol, "side": side}
    headers = get_headers(data)
    requests.post(url, headers=headers, data=json.dumps(data))
    current_position = None


def place_order(signal):
    global current_position
    balance = get_balance()
    position_size = round(balance * 0.5 * leverage, 2)
    side = "BUY" if signal == "buy" else "SELL"
    current_position = "long" if signal == "buy" else "short"

    # Dummy price used for now (price=0 for market order)
    order_data = {
        "symbol": symbol,
        "price": 0,
        "vol": position_size,
        "side": side,
        "type": 1,  # 1 = Market
        "open_type": "isolated",
        "position_id": 0,
        "leverage": leverage,
        "external_oid": str(int(time.time() * 1000)),
        "stop_loss_price": 0,
        "take_profit_price": 0
    }
    headers = get_headers(order_data)
    response = requests.post(f"{BASE_URL}/api/v1/private/order/submit", headers=headers, data=json.dumps(order_data))
    print("Order Response:", response.text)


@app.route("/webhook", methods=["POST"])
def webhook():
    global current_position
    data = request.get_json()
    signal = data.get("signal")

    if signal not in ["buy", "sell"]:
        return jsonify({"error": "Invalid signal"}), 400

    if current_position:
        close_position()

    cancel_all_orders()
    place_order(signal)

    return jsonify({
        "response": {
            "code": 200,
            "msg": f"Signal {signal} empfangen"
        },
        "status": "ok"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
