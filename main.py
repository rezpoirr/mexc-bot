from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import requests
import os

app = Flask(__name__)

# 🔐 ENV-Variablen
API_KEY = os.getenv("MEXC_API_KEY")
API_SECRET = os.getenv("MEXC_API_SECRET")
BASE_URL = "https://contract.mexc.com"

# 📈 Trading-Konfiguration
SYMBOL = os.getenv("SYMBOL", "USELESSUSDT")
LEVERAGE = 50
TP_PERCENT = 0.02
SL_PERCENTAGES = [0.005, 0.0051, 0.0052, 0.0053, 0.0054, 0.0055]

current_position = None

# 📦 HMAC Signatur
def sign_params(params):
    sorted_params = sorted(params.items())
    query_string = "&".join(f"{key}={value}" for key, value in sorted_params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return f"{query_string}&signature={signature}"

# 🔐 Header
def get_headers():
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "ApiKey": API_KEY
    }

# 💰 Kontostand
def get_balance():
    path = "/api/v1/private/account/assets"
    timestamp = str(int(time.time() * 1000))
    params = {"timestamp": timestamp}
    url = f"{BASE_URL}{path}?{sign_params(params)}"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        data = response.json()
        for asset in data.get("data", []):
            if asset["currency"] == "USDT":
                return float(asset["availableBalance"])
    return 0.0

# 🧠 Webhook-Route
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    signal = data.get("signal")

    if signal not in ["buy", "sell"]:
        return jsonify({"error": "Invalid signal"}), 400

    print(f"📩 Signal empfangen: {signal}")

    # Beispiel: Logge Kontostand
    balance = get_balance()
    print(f"💰 Aktueller USDT-Bestand: {balance}")

    # Später kann hier Order-Code rein
    return jsonify({"msg": f"Signal {signal} empfangen", "status": "ok"})

# 🛠 Start der App
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
