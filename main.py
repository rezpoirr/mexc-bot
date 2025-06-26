import os
import time
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ['API_KEY']
API_SECRET = os.environ['API_SECRET']
BASE_URL = "https://api.mexc.com"

symbol = "USELESSUSDT"
leverage = 50
tp_percent = 0.02
sl_percents = [0.0050, 0.0051, 0.0052, 0.0053, 0.0054, 0.0055]

current_position = None  # 'buy', 'sell', or None

def sign_request(params):
    query_string = "&".join([f"{k}={params[k]}" for k in sorted(params)])
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return query_string + f"&signature={signature}"

def get_balance():
    timestamp = str(int(time.time() * 1000))
    params = {
        "timestamp": timestamp,
    }
    signed = sign_request(params)
    headers = {"X-MEXC-API-KEY": API_KEY}
    url = f"{BASE_URL}/api/v3/account?{signed}"
    r = requests.get(url, headers=headers)
    return float(r.json()['balances'][0]['free'])

def cancel_all():
    params = {
        "symbol": symbol,
        "timestamp": str(int(time.time() * 1000)),
    }
    signed = sign_request(params)
    url = f"{BASE_URL}/api/v1/private/futures/order/cancel-all?{signed}"
    headers = {"X-MEXC-API-KEY": API_KEY}
    r = requests.delete(url, headers=headers)
    print(f"❌ Cancel All Response: {r.text}")

def place_order(side):
    balance = get_balance()
    amount_usdt = balance * 0.5
    print(f"📊 Balance: {balance}, Using: {amount_usdt} USDT")

    # Get current price
    ticker = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}").json()
    entry_price = float(ticker["price"])
    quantity = round((amount_usdt * leverage) / entry_price, 2)
    
    # Open order
    params = {
        "symbol": symbol,
        "price": 0,
        "vol": quantity,
        "side": 1 if side == "buy" else 2,
        "type": 1,
        "open_type": 1,
        "position_id": 0,
        "leverage": leverage,
        "external_oid": str(int(time.time())),
        "stop_loss_price": 0,
        "take_profit_price": 0,
        "position_mode": 1,
        "reduce_only": False,
        "timestamp": str(int(time.time() * 1000))
    }

    signed = sign_request(params)
    headers = {"X-MEXC-API-KEY": API_KEY}
    url = f"{BASE_URL}/api/v1/private/futures/order/place?{signed}"
    r = requests.post(url, headers=headers)
    print(f"📥 Order Response: {r.text}")

@app.route("/webhook", methods=["POST"])
def webhook():
    global current_position
    data = request.json
    signal = data.get("signal")

    if signal not in ["buy", "sell"]:
        return jsonify({"error": "Invalid signal"}), 400

    print(f"📩 Signal empfangen: {signal}")

    if current_position and current_position != signal:
        cancel_all()
        print(f"🔁 Bestehende Position geschlossen")

    place_order(signal)
    current_position = signal

    return jsonify({"status": "ok", "msg": f"Signal {signal} verarbeitet"})

if __name__ == "__main__":
    app.run(debug=True)
