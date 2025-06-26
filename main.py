import os
import time
import json
from flask import Flask, request, jsonify
from mexc_futures_api import MexcFutures

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

client = MexcFutures(API_KEY, API_SECRET)

symbol = "USELESSUSDT"
leverage = 50
tp_percent = 0.02
sl_levels = [0.005, 0.0051, 0.0052, 0.0053, 0.0054, 0.0055]
current_position = None  # "long" oder "short"


def get_balance():
    account_info = client.get_account_information()
    return float(account_info["availableBalance"])


def get_last_price():
    ticker = client.get_latest_price(symbol=symbol)
    return float(ticker["price"])


def close_position():
    global current_position
    if current_position:
        side = "SELL" if current_position == "long" else "BUY"
        try:
            client.close_position(symbol=symbol, side=side)
        except Exception as e:
            print("Fehler beim Schließen der Position:", e)
        current_position = None


def place_order(signal):
    global current_position
    balance = get_balance()
    last_price = get_last_price()

    trade_size_usdt = balance * 0.5
    quantity = round((trade_size_usdt * leverage) / last_price, 2)
    side = "BUY" if signal == "buy" else "SELL"
    current_position = "long" if side == "BUY" else "short"

    # TP und SL berechnen
    if side == "BUY":
        tp_price = round(last_price * (1 + tp_percent), 4)
        sl_prices = [round(last_price * (1 - sl), 4) for sl in sl_levels]
    else:
        tp_price = round(last_price * (1 - tp_percent), 4)
        sl_prices = [round(last_price * (1 + sl), 4) for sl in sl_levels]

    # Market Order öffnen
    try:
        response = client.create_order(
            symbol=symbol,
            side=side,
            type="market",
            quantity=quantity,
            leverage=leverage
        )
        print(f"{side} Order platziert mit {quantity} USELESSUSDT")

        # TP Order
        client.create_order(
            symbol=symbol,
            side="SELL" if side == "BUY" else "BUY",
            type="take_profit_market",
            stopPrice=tp_price,
            quantity=quantity,
            leverage=leverage
        )
        print(f"TP gesetzt bei {tp_price}")

        # SL Orders
        for idx, sl_price in enumerate(sl_prices):
            client.create_order(
                symbol=symbol,
                side="SELL" if side == "BUY" else "BUY",
                type="stop_market",
                stopPrice=sl_price,
                quantity=quantity,
                leverage=leverage
            )
            print(f"SL {idx+1} gesetzt bei {sl_price}")

    except Exception as e:
        print("Fehler beim Platzieren der Order:", e)


@app.route("/webhook", methods=["POST"])
def webhook():
    global current_position
    data = request.get_json()
    signal = data.get("signal")

    if signal not in ["buy", "sell"]:
        return jsonify({"status": "error", "msg": "Ungültiges Signal"})

    if current_position:
        close_position()

    place_order(signal)

    return jsonify({
        "status": "ok",
        "msg": f"Signal {signal} empfangen und Trade platziert"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
