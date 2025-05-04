from flask import Flask, request, jsonify
import os
import json
from binance.client import Client
from binance.enums import *

app = Flask(__name__)

binance_api_key = os.getenv("BINANCE_API_KEY", "YOUR_API_KEY")
binance_api_secret = os.getenv("BINANCE_API_SECRET", "YOUR_API_SECRET")

client = Client(binance_api_key, binance_api_secret, tld='com', testnet=False)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_data().decode('utf-8')
        if not data:
            print("Webhook verisi boş")
            return jsonify({"error": "Boş veri alındı"}), 400

        webhook_data = json.loads(data)

        action = webhook_data.get('action')
        symbol = webhook_data.get('symbol')
        usdt_quantity = float(webhook_data.get('quantity', 0))  # USDT cinsinden miktar
        label = webhook_data.get('label')
        kademe = webhook_data.get('kademe')
        reason = webhook_data.get('reason')

        # Sembol doğrulama
        try:
            symbol_info = client.get_symbol_info(symbol)
            print(f"Symbol info: {symbol_info}")  # Sembol bilgilerini logla
        except Exception as e:
            print(f"Geçersiz sembol: {symbol}, hata: {str(e)}")
            return jsonify({"error": f"Geçersiz sembol: {symbol}, hata: {str(e)}"}), 400

        # Mevcut fiyatı al
        ticker = client.get_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])

        # USDT miktarını coin adedine çevir
        quantity = usdt_quantity / price
        # quantityPrecision yerine stepSize kullanarak hassasiyeti hesapla
        step_size = float(symbol_info['filters'][0]['stepSize'])  # İlk filter genellikle lot size filtresi
        precision = int(round(-math.log10(step_size), 0)) if step_size else 8  # stepSize’a göre hassasiyet
        quantity = round(quantity, precision)

        print(f"Webhook alındı: action={action}, symbol={symbol}, usdt_quantity={usdt_quantity}, coin_quantity={quantity}, price={price}")

        if action == "buy":
            order = client.create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            print(f"Buy order placed (Futures): {order}")
        elif action == "sell":
            order = client.create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            print(f"Sell order placed (Futures): {order}")
        elif action == "close_all":
            account_info = client.futures_account()
            for position in account_info['positions']:
                if float(position['positionAmt']) != 0 and position['symbol'] == symbol:
                    side = SIDE_SELL if float(position['positionAmt']) > 0 else SIDE_BUY
                    quantity = abs(float(position['positionAmt']))
                    order = client.create_order(
                        symbol=symbol,
                        side=side,
                        type=ORDER_TYPE_MARKET,
                        quantity=quantity
                    )
                    print(f"Position closed for {symbol}: {order}")

        return jsonify({"status": "success"}), 200
    except json.JSONDecodeError as e:
        print(f"Webhook verisi geçersiz JSON formatında: {str(e)}")
        return jsonify({"error": "Geçersiz JSON formatı"}), 400
    except Exception as e:
        print(f"Webhook işlenirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
