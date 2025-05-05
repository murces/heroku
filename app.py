from flask import Flask, request, jsonify
import os
import json
import math
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
        quantity = float(webhook_data.get('quantity', 0))
        label = webhook_data.get('label')
        kademe = webhook_data.get('kademe')
        reason = webhook_data.get('reason')

        # Sembol doğrulama
        try:
            symbol_info = client.futures_exchange_info()
            valid_symbols = [s['symbol'] for s in symbol_info['symbols']]
            if symbol not in valid_symbols:
                raise ValueError("Sembol geçersiz.")
        except Exception as e:
            print(f"Geçersiz sembol: {symbol}, hata: {str(e)}")
            return jsonify({"error": f"Geçersiz sembol: {symbol}, hata: {str(e)}"}), 400

        # Mevcut fiyat
        ticker = client.futures_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])

        # Hassasiyet (stepSize)
        step_size = 1.0
        for s in symbol_info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = float(f['stepSize'])
                        break
        precision = int(round(-math.log10(step_size), 0)) if step_size else 8
        quantity = round(quantity, precision)

        print(f"Webhook alındı: action={action}, symbol={symbol}, coin_quantity={quantity}, price={price}")

        # BUY → LONG pozisyon
        if action == "buy":
            order = client.futures_create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
                positionSide='LONG'
            )
            print(f"Buy LONG order placed: {order}")

        # SELL → SHORT pozisyon
        elif action == "sell":
            order = client.futures_create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
                positionSide='SHORT'
            )
            print(f"Sell SHORT order placed: {order}")

        # Tüm pozisyonları kapat
        elif action == "close_all":
            client.futures_cancel_all_open_orders(symbol=symbol)
            account_info = client.futures_account()
            for position in account_info['positions']:
                if position['symbol'] == symbol and float(position['positionAmt']) != 0:
                    side = SIDE_SELL if float(position['positionAmt']) > 0 else SIDE_BUY
                    pos_qty = abs(float(position['positionAmt']))
                    pos_side = 'LONG' if float(position['positionAmt']) > 0 else 'SHORT'

                    order = client.futures_create_order(
                        symbol=symbol,
                        side=side,
                        type=ORDER_TYPE_MARKET,
                        quantity=pos_qty,
                        positionSide=pos_side
                    )
                    print(f"Pozisyon kapatıldı ({pos_side}): {order}")

        return jsonify({"status": "success"}), 200

    except json.JSONDecodeError as e:
        print(f"Webhook verisi geçersiz JSON formatında: {str(e)}")
        return jsonify({"error": "Geçersiz JSON formatı"}), 400
    except Exception as e:
        print(f"Webhook işlenirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
