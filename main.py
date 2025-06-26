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

SYMBOL = os.getenv("SYMBOL")  # z. B. USELESSUSDT
LEVERAGE = 50
TP_PERCENT = 0.02
SL_PERCENTAGES = [0.005, 0.0051, 0.0052, 0.0053, 0.0054, 0.0055]

current_position = None

def sign_params(params):
    sorted_params = sorted(params.items())
    query_string = "&".join(f"{key}={value}" for key, value in sorted_params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return query_string + f"&sign={signature}"

def get_headers():
    return {
        "Content-Type": "application/json",
        "ApiKey": API_KEY
    }

def get_balance():
    url = f"{BASE_URL}/api/v1/private/account/assets"
    timestamp = str(int(time.time() * 1000))
    params = {
        "timestamp": timestamp
    }
    signed_query = sign_params(params)
    full_url = f"{url}?{signed_query}"
    response = requests.get(full_url, headers=get_headers())
    data = response.json()
    for asset in data.get("data", []):
        if asset.get("currency") == "USDT":
            return float(asset.get("availableBalance", 0))
    return 0.0

def place_order(signal):
    global current_position

    side = 1 if signal == "buy" else 2  # 1 = buy/long, 2 = sell/short
    close_side = 2 if signal == "buy" else 1
    balance = get_balance()
    order_value = balance * 0.5 * LEVERAGE

    url = f"{BASE_URL}/api/v1/private/order/submit"
    timestamp = str(int(time.time() * 1000))
    order_data = {
        "symbol": SYMBOL,
        "price": 0,  # market order
        "vol": round(order_value, 2),
        "leverage": LEVERAGE,
        "side": side,
        "type": 1,  # 1 = market
        "open_type": "isolated",
        "position_id": 0,
        "external_oid": str(int(time.time())),
        "stop_loss_price": 0,
        "take_profit_price": 0,
        "timestamp": timestamp
    }

    signed_query = sign_params(order_data)
    full_url = f"{url}?{signed_query}"

    response = requests.post(full_url, headers=get_headers())
    print(f"Order response: {response.text}")

    if response.status_code == 200 and response.json().get("success"):
        print(f"Order erfolgreich: {signal}")
        current_position = signal
        set_tp_sl(signal)
    else:
        print(f"Order fehlgeschlagen: {response.text}")

def set_tp_sl(signal):
    direction = 1 if signal == "buy" else -1
    current_price = get_market_price()
    tp_price = round(current_price * (1 + direction * TP_PERCENT), 4)

    for i, sl_pct in enumerate(SL_PERCENTAGES):
        sl_price = round(current_price * (1 - direction * sl_pct), 4)
        print(f"Set SL-{i+1}: {sl_price}")

    print(f"Set TP: {tp_price}")

def get_market_price():
    url = f"{BASE_URL}/api/v1/contract/market_price?symbol={SYMBOL}"
    response = requests.get(url)
    data = response.json()
    return float(data.get("data", {}).get("price", 0))

@app.route("/webhook", methods=["POST"])
def webhook():
    global current_position
    data = request.get_json()
    signal = data.get("signal")

    if signal not in ["buy", "sell"]:
        return jsonify({"error": "Ungültiges Signal"}), 400

    print(f"Webhook-Signal empfangen: {signal}")

    if current_position != signal:
        print(f"Starte neuen Trade: {signal}")
        place_order(signal)
    else:
        print(f"Signal {signal} ignoriert – bereits in Position.")

    return jsonify({"msg": f"Signal {signal} empfangen", "status": "ok"})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
