
import os, hmac, time, hashlib, requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# API-Keys aus Umgebungsvariablen
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

SYMBOL = "USELESSUSDT_PERP"
LEVERAGE = 50
TP = 0.02
SL_LEVELS = [0.0050, 0.0051, 0.0052, 0.0053, 0.0054]

def sign(params):
    qs = "&".join(f"{k}={params[k]}" for k in sorted(params))
    return hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()

def mexc_request(path, params, signed=True):
    url = "https://api.mexc.com" + path
    headers = {"ApiKey": API_KEY}
    if signed:
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = sign(params)
    return requests.post(url, json=params, headers=headers)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    signal = data.get("signal")

    if signal == "buy":
        order = {
            "symbol": SYMBOL,
            "priceProtect": True,
            "side": "BUY",
            "type": "MARKET",
            "quantity": 1
        }
        response = mexc_request("/api/v1/private/order", order)
        return jsonify({"status": "ok", "response": response.json()})
    return jsonify({"status": "ignored"})
