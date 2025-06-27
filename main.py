import os
import time
import threading
import requests
import hmac
import hashlib
from urllib.parse import urlencode
from fastapi import FastAPI, Request
import uvicorn

# --- ENVIRONMENT CONFIG ---
API_KEY = os.getenv("MEXC_API_KEY")
API_SECRET = os.getenv("MEXC_API_SECRET")
SYMBOL = os.getenv("SYMBOL", "USELESSUSDT_PERP")
PORT = int(os.getenv("PORT", 10000))
LEVERAGE = 50
USE_BALANCE_PCT = 0.5

# --- GLOBAL STATE ---
signal_store = {"signal": None}
position = {"side": None, "entry": None, "open": False}

# --- MEXC BYPASS FUNCTIONS ---
def sign_payload(payload):
    payload["api_key"] = API_KEY
    payload["req_time"] = int(time.time() * 1000)
    sign = hmac.new(API_SECRET.encode(), urlencode(payload).encode(), hashlib.sha256).hexdigest()
    payload["sign"] = sign
    return payload

def bypass_create_order(side, qty):
    side_code = 1 if side == "BUY" else 2
    data = {
        "symbol": SYMBOL,
        "price": 0,
        "vol": round(qty, 2),
        "side": side_code,
        "type": 1,  # Market
        "open_type": "isolated",
        "position_id": 0,
        "leverage": LEVERAGE,
        "external_oid": "twin-range-bot"
    }
    res = requests.post("https://contract.mexc.com/api/v1/private/order/submit", data=sign_payload(data))
    return res.json()

def bypass_cancel_all():
    data = {"symbol": SYMBOL}
    res = requests.post("https://contract.mexc.com/api/v1/private/order/cancelAll", data=sign_payload(data))
    return res.json()

def get_balance():
    res = requests.get("https://contract.mexc.com/api/v1/private/account/assets", params=sign_payload({}))
    for x in res.json().get("data", []):
        if x["currency"] == "USDT":
            return float(x["availableBalance"])
    return 0.0

def get_mark_price():
    res = requests.get(f"https://contract.mexc.com/api/v1/contract/market/price?symbol={SYMBOL}")
    return float(res.json()["data"]["markPrice"])

# --- WEBHOOK SERVER ---
app = FastAPI()

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    signal = data.get("signal")
    if signal in ["BUY", "SELL"]:
        signal_store["signal"] = signal
        print(f"📩 Webhook received: {signal}")
        return {"status": "ok"}
    return {"error": "invalid signal"}

# --- TRADING LOOP ---
def trade_loop():
    while True:
        signal = signal_store["signal"]
        price = get_mark_price()

        if position["open"]:
            tp = position["entry"] * 1.02
            sls = [position["entry"] * (1 - s) for s in [0.005, 0.051, 0.052, 0.053, 0.054, 0.055]]
            if price >= tp or any(price <= sl for sl in sls):
                bypass_cancel_all()
                print(f"📤 Position closed @ {price:.5f} (TP/SL)")
                position.update({"side": None, "entry": None, "open": False})

        if signal and (not position["open"] or signal != position["side"]):
            if position["open"]:
                bypass_cancel_all()
                print(f"↩️ Exiting old {position['side']} position")
                position.update({"side": None, "entry": None, "open": False})

            balance = get_balance()
            qty = (balance * USE_BALANCE_PCT * LEVERAGE) / price
            res = bypass_create_order(signal, qty)

            if res.get("success"):
                position.update({"side": signal, "entry": price, "open": True})
                print(f"🟢 New {signal} @ {price:.5f}, qty={qty:.2f}")
                signal_store["signal"] = None
            else:
                print(f"❌ Order failed: {res}")
        time.sleep(2)

# --- MAIN ENTRY ---
if __name__ == "__main__":
    threading.Thread(target=trade_loop).start()
    uvicorn.run(app, host="0.0.0.0", port=PORT)

