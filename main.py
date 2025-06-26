import os
import hmac
import time
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# === MEXC API Credentials from environment variables ===
API_KEY = os.environ.get("MEXC_API_KEY")
API_SECRET = os.environ.get("MEXC_API_SECRET")
BASE_URL = "https://api.mexc.com"

# === Global to track open position ===
current_position = None

# === Utility functions ===
def sign_request(params):
    sorted_params = sorted(params.items())
    query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

def get_headers():
    return {
        "Content-Type": "application/json",
        "ApiKey": API_KEY
    }

def get_balance():
    url = f"{BASE_URL}/api/v2/private/account/assets"
    timestamp = str(int(time.time() * 1000))
    params = {
        "timestamp": timestamp
    }
    params["signature"] = sign_request(params)
    response = requests.get(url, headers=get_headers(), params=params)
    data = response.json()
    for asset in data.get("data", []):
        if asset["asset"] == "USDT":
            return float(asset["availableBalance"])
    return 0.0

def close_position(symbol):
    print("⚠️ Schließe bestehende Position")
    order = {
        "symbol": symbol,
        "price": 0,  # Market
        "vol": 0,  # Dynamisch (nur bei Position)
        "side": 3,  # Close long
        "type": 1,  # Market
        "open_type": "close",
        "position_id": 0,
        "leverage": 50,
        "external_oid": f"close_{int(time.time())}",
        "stop_loss_price": 0,
        "take_profit_price": 0,
        "position_mode": "single",
        "reduce_only": True,
        "timestamp": str(int(time.time() * 1000))
    }
    order["signature"] = sign_request(order)
    r = requests.post(f"{BASE_URL}/api/v1/private/order/submit", headers=get_headers(), json=order)
    print(f"⛔️ Position geschlossen: {r.text}")

def place_order(signal):
    global current_position
    balance = get_balance()
    print(f"💰 Aktuelles Balance: {balance:.2f} USDT")

    if not balance or balance < 1:
        print("❌ Nicht genug Guthaben")
        return

    amount_usdt = balance * 0.5
    symbol = "USELESSUSDT"

    if current_position:
        close_position(symbol)
        current_position = None
        time.sleep(1)

    side = 1 if signal == "buy" else 2
    stop_losses = [0.005 + i * 0.0001 for i in range(6)]
    for i, sl in enumerate(stop_losses):
        order = {
            "symbol": symbol,
            "price": 0,
            "vol": round(amount_usdt / 0.123, 2),  # Dummy price (update!)
            "side": side,
            "type": 1,
            "open_type": "isolated",
            "position_id": 0,
            "leverage": 50,
            "external_oid": f"order_{i}_{int(time.time())}",
            "stop_loss_price": round(0.123 * (1 - sl), 5),
            "take_profit_price": round(0.123 * 1.02, 5),
            "position_mode": "single",
            "reduce_only": False,
            "timestamp": str(int(time.time() * 1000))
        }
        order["signature"] = sign_request(order)
        r = requests.post(f"{BASE_URL}/api/v1/private/order/submit", headers=get_headers(), json=order)
        print(f"📦 Order {i+1}: {r.text}")

    current_position = signal
    print(f"✅ Neue Position: {signal}")

# === Webhook endpoint ===
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    signal = data.get("signal")

    if signal in ["buy", "sell"]:
        print(f"📨 Signal empfangen: {signal}")
        place_order(signal)
        return jsonify({"status": "ok", "msg": f"Signal {signal} empfangen"}), 200
    else:
        return jsonify({"status": "error", "msg": "Ungültiges Signal"}), 400

# === Server für Render ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
