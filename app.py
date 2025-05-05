from flask import Flask, request, jsonify
import os
import json
import math
from binance.client import Client
from binance.enums import *

app = Flask(__name__)

# Binance API anahtarlarını ortam değişkenlerinden al
binance_api_key = os.getenv("BINANCE_API_KEY", "YOUR_API_KEY")
binance_api_secret = os.getenv("BINANCE_API_SECRET", "YOUR_API_SECRET")

# Binance client (Futures için de geçerli)
client = Client(binance_api_key, binance_api_secret, tld='com')

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
        quantity = float(webhook_data.get('quantity', 0))  # Coin adedi
        label = webhook_data.get('label')
        kademe = webhook_data.get('kademe')
        reason = webhook_data.get('reason')

        # Futures sembol bilgilerini çek
        exchange_info = client.futures_exchange_info()
        symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)

        if not symbol_info:
            print(f"Geçersiz sembol: {symbol}")
            return jsonify({"error": f"Geçersiz sembol: {symbol}"}), 400

        # Mevcut futures fiyatı
        ticker = client.futures_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])

        # stepSize filtre bilgisi
        step_size = None
        for filt in symbol_info['filters']:
            if filt['filterType'] == 'LOT_SIZE':
                step_size = float(filt['stepSize'])
                break
        precision = int(round(-math.log10(step_size), 0)) if step_size else 3
        quantity = round(quantity, precision)

        print(f"Webhook alındı: action={action}, symbol={symbol}, coin_quantity={quantity}, price={price}")

        # (Opsiyonel) Kaldıraç ayarı
        client.futures_change_leverage(symbol=symbol, leverage=5)

        # İşlem türüne göre emir gönder
        if action == "buy":
            order = client.futures_create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            print(f"Buy order placed (Futures): {order}")

        elif action == "sell":
            order = client.futures_create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            print(f"Sell order placed (Futures): {order}")

        elif action == "close_all":
            account_info = client.futures_account()
            for position in account_info['positions']:
                if position['symbol'] == symbol and float(position['positionAmt']) != 0:
                    close_side = SIDE_SELL if float(position['positionAmt']) > 0 else SIDE_BUY
                    close_qty = abs(float(position['positionAmt']))
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=close_side,
                        type=ORDER_TYPE_MARKET,
                        quantity=close_qty
                    )
                    print(f"Pozisyon kapatıldı: {symbol}, Emir: {order}")

        return jsonify({"status": "success"}), 200

    except json.JSONDecodeError as e:
        print(f"Geçersiz JSON formatı: {str(e)}")
        return jsonify({"error": "Geçersiz JSON"}), 400
    except Exception as e:
        print(f"İşlem sırasında hata: {str(e)}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
