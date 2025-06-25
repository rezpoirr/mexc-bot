from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Hole API Keys aus Umgebungsvariablen
API_KEY = os.getenv("MEXC_API_KEY")
API_SECRET = os.getenv("MEXC_API_SECRET")

@app.route('/')
def home():
    return "Bot läuft!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    if not data or 'signal' not in data:
        return jsonify({'response': {'code': 400, 'msg': 'Invalid payload'}, 'status': 'error'}), 400

    signal = data['signal']
    print(f"Empfangenes Signal: {signal}")

    # Hier würdest du den Trade-Logik-Code einfügen
    # aktuell nur Test-Rückmeldung
    return jsonify({'response': {'code': 200, 'msg': f'Signal {signal} empfangen'}, 'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
