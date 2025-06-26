from flask import Flask, request, jsonify
import hmac, hashlib, time, requests, os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv("MEXC_API_KEY")
API_SECRET = os.getenv("MEXC_API_SECRET")
BASE = "https://contract.mexc.com"
SYMBOL = os.getenv("SYMBOL", "USELESSUSDT_USDT")
LEVERAGE = 50
OPEN_TYPE = "isolated"

def sign(params):
    qs = "&".join(f"{k}={params[k]}" for k in sorted(params))
    sig = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    return qs + "&signature=" + sig

def headers():
    return {
        "Content-Type": "application/json",
        "ApiKey": API_KEY
    }

def get_futures_balance():
    ts = str(int(time.time() * 1000))
    params = {"timestamp": ts}
    url = f"{BASE}/api/v1/private/account/assets?{sign(params)}"
    r = requests.get(url, headers=headers()).json()
    for cur in r.get("data", []):
        if cur["currency"] == "USDT":
            return float(cur["available_balance"])
    return 0.0

def get_price():
    r = requests.get(f"{BASE}/api/v1/contract/market/depth?symbol={SYMBOL}&depth=5").json()
    bids = float(r["data"]["bids"][0][0])
    asks = float(r["data"]["asks"][0][0])
    return (bids + asks) / 2

def place_order(signal):
    bal = get_futures_balance()
    price = get_price()
    use = bal * 0.5
    vol = round(use * LEVERAGE / price, 3)
    side = 1 if signal=="buy" else 2

    params = {
        "symbol": SYMBOL,
        "price": 0,
        "vol": vol,
        "leverage": LEVERAGE,
        "side": side,
        "type": 1,
        "open_type": OPEN_TYPE,
        "position_id": 0,
        "external_oid": str(int(time.time()*1000)),
        "reduce_only": False,
        "timestamp": str(int(time.time()*1000))
    }

    url = f"{BASE}/api/v1/private/order/submit?{sign(params)}"
    res = requests.post(url, headers=headers()).json()
    print(f"📤 Sende Order: {res}")
    return res

@app.route("/webhook", methods=["POST"])
def webhook():
    s = request.json.get("signal","").lower()
    if s not in ["buy","sell"]:
        return jsonify({"error": "ungültig"}), 400
    res = place_order(s)
    return jsonify(res), (200 if res.get("status")=="ok" else 400)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
