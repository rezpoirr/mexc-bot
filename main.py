import os
import hmac
import time
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# API-Schlüssel aus Umgebungsvariablen (passen zu Render "Environment" Settings)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Basis-Konfiguration
SYMBOL = "USELESSUSDT_PERP"
LEVERAGE = 50
TP = 0.02
SL_LEVELS = [0.0050, 0.0051, 0.0052, 0.0053, 0.0054]

def sign(params):
    query_string = "&".join([f"{k}={params[k]}" for k in sorted(params)])
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

def mexc_request(path, params, signed=True):
    url = f"https://api.mexc.com{path}"
    headers = {"ApiKey": API_KEY}

    if signed:
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = sign(params)

    response = requests.post(url, params=params, headers=headers)
    return response.json()

@app.route("/", methods=["GET"])
def home():
    return "✅ MEXC Bot läuft!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data or "signal" not in data:
        return jsonify({"error": "Kein gültiges Signal erhalten"}), 400

    signal = data["signal"]

    if signal == "buy":
        return jsonify({"status": "ok", "aktion": "buy"})  # << später Mexc Order logik
    elif signal == "sell":
        return jsonify({"status": "ok", "aktion": "sell"})
    else:
        return jsonify({"error": "Unbekanntes Signal"}), 400

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
