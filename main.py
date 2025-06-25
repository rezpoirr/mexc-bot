from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "MEXC Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'signal' not in data:
        return jsonify({'status': 'error', 'message': 'No signal provided'}), 400
    
    signal = data['signal']
    print(f"Signal erhalten: {signal}")

    # Hier kannst du später deine Trading-Logik einbauen
    return jsonify({'status': 'ok', 'message': f'Signal empfangen: {signal}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
