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
current_position = None  # 'long', 'short' oder None


def sign_request(req_time, sign_params):
    query_string = '&'.join([f"{key}={value}" for key, value in sign_params.items()])
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
    try:
        url = f"{BASE_URL}/api/v1/private/account/assets"
        headers = get_headers()
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        for item in data['data']:
            if item['currency'] == 'USDT':
                return float(item['availableBalance'])
    except Exception as e:
        print("Fehler beim Abrufen des Guthabens:", e)
    return 0


def cancel_open_orders():
    try:
        url = f"{BASE_URL}/api/v1/private/order/cancel-all"
        data = {"symbol": symbol}
        headers = get_headers(data)
        requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
    except Exception as e:
        print("Fehler beim Stornieren offener Orders:", e)


def close_position():
    global current_position
    if current_position:
        try:
            side = "SELL" if current_position == "long" else "BUY"
            url = f"{BASE_URL}/api/v1/private/order/close-position"
            data = {
                "symbol": symbol,
                "side": side
            }
            headers = get_headers(data)
            requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
            current_position = None
        except Exception as e:
            print("Fehler beim Schließen der Position:", e)


def place_trade(signal):
    global current_position
    balance = get_balance()
    if balance == 0:
        print("Kein Guthaben verfügbar!")
        return

    trade_size = round((balance * 0.5) * leverage, 2)
    side = "BUY" if signal == "buy" else "SELL"
    current_position = "long" if side == "BUY" else "short"

    url = f"{BASE_URL}/api/v1/private/order/submit"
    data = {
        "symbol": symbol,
        "price": 0,
        "vol": trade_size,
        "side": side,
        "type": 1,
        "open_type": "isolated",
        "position_id": 0,
        "leverage": leverage,
        "external_oid": str(int(time.time() * 1000)),
        "stop_loss_price": 0,
        "take_profit_price": 0
    }
    headers = get_headers(data)
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
        print("Trade placed:", response.json())
    except Exception as e:
        print("Fehler beim Platzieren des Trades:", e)


@app.route("/webhook", methods=["POST"])
def webhook():
    global current_position
    try:
        data = request.get_json()
        signal = data.get("signal")

        if signal not in ["buy", "sell"]:
            return jsonify({"response": {"code": 400, "msg": "Ungültiges Signal"}, "status": "error"})

        if current_position:
            close_position()

        cancel_open_orders()
        place_trade(signal)

        return jsonify({
            "response": {
                "code": 200,
                "msg": f"Signal {signal} empfangen"
            },
            "status": "ok"
        })
    except Exception as e:
        print("Fehler im Webhook:", e)
        return jsonify({"response": {"code": 500, "msg": "Interner Fehler"}, "status": "error"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
