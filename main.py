import os
import time
import requests
import hmac, hashlib

API_KEY = os.getenv("MEXC_API_KEY")
API_SECRET = os.getenv("MEXC_API_SECRET")
SYMBOL = os.getenv("SYMBOL", "USELESSUSDT")
LEVERAGE = 50
USE_BALANCE_PCT = 0.5

# --- Bypass-Funktionen (vereinfacht) ---
def sign_payload(payload: dict):
    payload["api_key"] = API_KEY
    payload["req_time"] = int(time.time() * 1000)
    payload["sign"] = hmac.new(API_SECRET.encode(), urlencode(payload).encode(), hashlib.sha256).hexdigest()
    return payload

def bypass_create_order(side, qty):
    payload = {"symbol": SYMBOL, "price": 0, "vol": qty, "side": 1 if side=="BUY" else 2,
               "type": 1, "open_type": "isolated", "position_id":0, "leverage":LEVERAGE, "external_oid":"bot"}
    r = requests.post("https://www.mexc.com/api/v1/private/order/submit",
                      data=sign_payload(payload), timeout=5)
    return r.json()

def bypass_cancel_all():
    payload = {"symbol": SYMBOL}
    r = requests.post("https://www.mexc.com/api/v1/private/order/cancelAll",
                      data=sign_payload(payload), timeout=5)
    return r.json()

def bypass_get_balance():
    payload = {}
    r = requests.get("https://www.mexc.com/api/v1/private/account/info",
                     params=sign_payload(payload), timeout=5)
    data = r.json()
    for c in data["data"]:
        if c["currency"] == "USDT": return float(c["availableBalance"])
    return 0.0

def bypass_get_mark_price():
    r = requests.get(f"https://www.mexc.com/api/v1/contract/market/price?symbol={SYMBOL}")
    return float(r.json()["data"]["markPrice"])

# --- Heikin-Ashi Dummy-Signal (einfacher Platzhalter) ---
def get_heikin_signal():
    # Hier deine Logik einfügen
    # Beispiel: return "BUY", "SELL" oder None
    return None

# --- Hauptlogik ---
def main():
    position_open = False
    position_side = None
    entry_price = None
    qty = 0

    while True:
        signal = get_heikin_signal()
        mark = bypass_get_mark_price()

        if position_open:
            tp = entry_price * 1.02
            sl_targets = [entry_price * (1 - x) for x in [0.005, 0.051,0.052,0.053,0.054,0.055]]
            if mark >= tp or any(mark <= sl for sl in sl_targets):
                bypass_cancel_all()
                position_open = False
                log = f"📉 Closed {position_side} @ {mark:.5f}"
                print(log)

        if signal and (not position_open or position_side != signal):
            if position_open:
                bypass_cancel_all()
            bal = bypass_get_balance()
            qty = bal * USE_BALANCE_PCT * LEVERAGE / mark
            res = bypass_create_order(signal, qty)
            if res.get("success", False):
                entry_price = mark
                position_open = True
                position_side = signal
                print(f"🟢 Opened {signal} @ {mark:.5f}, qty={qty:.2f}")
            else:
                print("❌ Order failed:", res)
        time.sleep(1)

if __name__ == "__main__":
    main()
