from flask import Flask, request, jsonify
import os
import json
from binance.client import Client
from binance.enums import *

app = Flask(__name__)

# Binance API kimlik bilgileri (environment variables ile)
binance_api_key = os.getenv("BINANCE_API_KEY", "YOUR_API_KEY")
binance_api_secret = os.getenv("BINANCE_API_SECRET", "YOUR_API_SECRET")

# Binance Futures istemcisi (gerçek mod)
client = Client(binance_api_key, binance_api_secret, tld='com', testnet=False)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Ham veriyi al
        data = request.get_data().decode('utf-8')
        if not data:
            print("Webhook verisi boş")
            return jsonify({"error": "Boş veri alındı"}), 400

        # JSON’a dönüştür
        webhook_data = json.loads(data)

        action = webhook_data.get('action')
        symbol = webhook_data.get('symbol')
        quantity = float(webhook_data.get('quantity', 0))
        label = webhook_data.get('label')
        kademe = webhook_data.get('kademe')
        reason = webhook_data.get('reason')

        print(f"Webhook alındı: action={action}, symbol={symbol}, quantity={quantity}")

        if action == "buy":
            order = client.create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            print(f"Buy order placed: {order}")
        elif action == "sell":
            order = client.create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            print(f"Sell order placed: {order}")
        elif action == "close_all":
            account_info = client.futures_account()
            for position in account_info['positions']:
                if float(position['positionAmt']) != 0:
                    side = SIDE_SELL if float(position['positionAmt']) > 0 else SIDE_BUY
                    quantity = abs(float(position['positionAmt']))
                    order = client.create_order(
                        symbol=symbol,
                        side=side,
                        type=ORDER_TYPE_MARKET,
                        quantity=quantity
                    )
            print(f"All positions closed for {symbol}")

        return jsonify({"status": "success"}), 200
    except json.JSONDecodeError as e:
        print(f"Webhook verisi geçersiz JSON formatında: {str(e)}")
        return jsonify({"error": "Geçersiz JSON formatı"}), 400
    except Exception as e:
        print(f"Webhook işlenirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
