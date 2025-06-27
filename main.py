from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import requests
import os

app = Flask(__name__)

# 🔐 Environment-Variablen
API_KEY = os.getenv("MEXC_API_KEY")
API_SECRET = os.getenv("MEXC_API_SECRET")
BASE_URL = "https://contract.mexc.com"

# 📈 Trading-Einstellungen
SYMBOL = os.getenv("SYMBOL", "USELESSUSDT_PERP")
LEVERAGE = 50
ORDER_TYPE = 1         # Market
POSITION_MODE = 1      # Single Position
OPEN_TYPE = "isolated" # Isoliert

# 🔏 Signiere alle Parameter
def sign_params(params):
    sorted_params = sorted(params.items())
    query = "&".join(f"{k}={v}" for k, v in sorted_params)
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    return f"{query}&signature={signature}"

# 🧾 Authentifizierungs-Header
def get_headers():
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "ApiKey": API_KEY
    }

# 💰 Aktuelles USDT-Futures-Guthaben abrufen
def get_balance():
    url = f"{BASE_URL}/api/v1/private/account/asset"
    timestamp = str(int(time.time() * 1000))
    params = {"timestamp": timestamp}
    full_url = f"{url}?{sign_params(params)}"
    response = requests.get(full_url, headers=get_headers())

    print("📦 API-Antwort (Balance):", response.text)

    try:
        result = response.json()
        for asset in result.get("data", []):
            if asset["currency"] == "USDT":
                balance = float(asset["availableBalance"])
                print(f"✅ Verfügbares USDT (Futures): {balance}")
                return balance
    except Exception as e:
        print("❌ Fehler beim Auslesen der Balance:", e)

    return 0.0

# 📤 Order senden
def place_futures_order(signal):
    side = 1 if signal == "buy" else 2
    timestamp = str(int(time.time() * 1000))
    balance = get_balance()

    if balance < 1:
        return {"error": f"Balance zu niedrig: {balance} USDT"}

    quantity = round(balance * LEVERAGE / 100, 3)
    print(f"📊 Order-Menge: {quantity} USELESSUSDT @ Leverage {LEVERAGE}x")

    order = {
        "symbol": SYMBOL,
        "price": 0,
        "vol": quantity,
        "leverage": LEVERAGE,
        "side": side,
        "type": ORDER_TYPE,
        "open_type": OPEN_TYPE,
        "position_id": 0,
        "external_oid": timestamp,
        "stop_loss_price": 0,
        "take_profit_price": 0,
        "position_mode": POSITION_MODE,
        "reduce_only": False,
        "timestamp": timestamp
    }

    signed = sign_params(order)
    url = f"{BASE_URL}/api/v1/private/order/submit?{signed}"
    response = requests.post(url, headers=get_headers())

    print(f"📤 Order-Antwort: {response.status_code} → {response.text}")
    return response.json()

# 🌐 Webhook-Route
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    signal = data.get("signal", "").lower()

    if signal not in ["buy", "sell"]:
        return jsonify({"error": "Ungültiges Signal"}), 400

    print(f"🚨 Webhook empfangen: {signal.upper()}")
    result = place_futures_order(signal)

    if "error" in result:
        return jsonify({"status": "error", "msg": result["error"]}), 400
    return jsonify({"status": "ok", "msg": f"Order {signal} gesendet", "result": result})

# ▶️ Lokaler Start (für Render wichtig)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
