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

SYMBOL = os.getenv("SYMBOL", "USELESSUSDT")
LEVERAGE = 50
POSITION_MODE = 1  # 1 = Single-Position Mode
ORDER_TYPE = 1     # 1 = Market Order
OPEN_TYPE = "isolated"

def sign_params(params):
    sorted_params = sorted(params.items())
    query_string = "&".join(f"{key}={value}" for key, value in sorted_params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return f"{query_string}&signature={signature}"

def get_headers():
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "ApiKey": API_KEY
    }

# ⚠️ Testweise Bypass → immer "20 USDT Guthaben"
def get_futures_balance():
    return 20.0

def place_futures_order(signal):
    side = 1 if signal == "buy" else 2  # 1 = Open Long, 2 = Open Short
    timestamp = str(int(time.time() * 1000))
    balance = get_futures_balance()

    quantity = round(balance * LEVERAGE / 100, 3)

    order = {
        "symbol": SYMBOL,
        "price": 0,
        "vol": quantity,
        "leverage": LEVERAGE,
        "side": side,
        "type": ORDER_TYPE,
        "open_type": OPEN_TYPE,
        "position_id": 0,
        "external_oid": str(timestamp),
        "stop_loss_price": 0,
        "take_profit_price": 0,
        "position_mode": POSITION_MODE,
        "reduce_only": False,
        "timestamp": timestamp
    }

    signed = sign_params(order)
    url = f"{BASE_URL}/api/v1/private/order/submit?{signed}"
    response = requests.post(url, headers=get_headers())

    print(f"📤 Order gesendet ({signal.upper()}): {response.status_code} {response.text}")
    return response.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    signal = data.get("signal", "").lower()

    if signal not in ["buy", "sell"]:
        return jsonify({"error": "Ungültiges Signal"}), 400

    print(f"🚨 Signal empfangen: {signal}")
    result = place_futures_order(signal)

    if "error" in result:
        return jsonify({"status": "error", "msg": result["error"]}), 400
    return jsonify({"status": "ok", "msg": f"Order {signal} gesetzt", "result": result})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
