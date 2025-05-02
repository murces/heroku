from flask import Flask, request
from binance.client import Client
import json
import os

app = Flask(__name__)

# Binance API anahtarları
binance_api_key = J6bPS62SQXaQiEn8qHkGpXTMHGm9Go7ZpVrMHzwNBBQOjvTjjuClX54JjrxjrpI0
binance_api_secret = xITUWsEJITJVIUk2H5fVlEs97Ws3xj1FzmBZhUaoo5U5roOi9gLCPYqGFolKgEMj
client = Client(binance_api_key, binance_api_secret)

# Binance Futures ayarları
symbol = "BTCUSDT"
client.futures_change_position_mode(dualSidePosition=True)  # Hedge Mode etkin

@app.route('/webhook', methods=['POST'])
def webhook():
    data = json.loads(request.data)
    
    action = data['action']  # buy, sell, close_all
    symbol = data['symbol']
    quantity = float(data['quantity']) if 'quantity' in data else 0
    label = data['label'] if 'label' in data else ""
    kademe = int(data['kademe'])
    reason = data['reason'] if 'reason' in data else ""

    try:
        # USDT miktarını coin miktarına çevir
        price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        coin_quantity = round(quantity / price, 3)  # Ör: 100 USDT / 50,000 USDT/BTC = 0.002 BTC

        # Bakiye kontrolü
        balance = float(client.futures_account()['availableBalance'])
        if action in ['buy', 'sell'] and quantity > balance:
            raise Exception(f"Yetersiz bakiye: Gerekli {quantity} USDT, Mevcut {balance} USDT")

        if action == 'buy':
            # Long pozisyon aç
            order = client.futures_create_order(
                symbol=symbol,
                side=Client.SIDE_BUY,
                positionSide="LONG",
                type=Client.ORDER_TYPE_MARKET,
                quantity=coin_quantity
            )
            print(f"Long pozisyon açıldı: {label}, Miktar: {coin_quantity}, Kademe: {kademe}")
        
        elif action == 'sell':
            # Short pozisyon aç
            order = client.futures_create_order(
                symbol=symbol,
                side=Client.SIDE_SELL,
                positionSide="SHORT",
                type=Client.ORDER_TYPE_MARKET,
                quantity=coin_quantity
            )
            print(f"Short pozisyon açıldı: {label}, Miktar: {coin_quantity}, Kademe: {kademe}")
        
        elif action == 'close_all':
            # Long pozisyonları kapat
            positions = client.futures_position_information(symbol=symbol)
            for position in positions:
                position_amount = float(position['positionAmt'])
                position_side = position['positionSide']
                if position_amount > 0 and position_side == "LONG":
                    client.futures_create_order(
                        symbol=symbol,
                        side=Client.SIDE_SELL,
                        positionSide="LONG",
                        type=Client.ORDER_TYPE_MARKET,
                        quantity=position_amount
                    )
                    print(f"Tüm long pozisyonlar kapatıldı: {position_amount}")
                elif position_amount < 0 and position_side == "SHORT":
                    client.futures_create_order(
                        symbol=symbol,
                        side=Client.SIDE_BUY,
                        positionSide="SHORT",
                        type=Client.ORDER_TYPE_MARKET,
                        quantity=abs(position_amount)
                    )
                    print(f"Tüm short pozisyonlar kapatıldı: {abs(position_amount)}")
            print(f"Tüm pozisyonlar kapatıldı: {reason}, Kademe: {kademe}")

        return {"status": "success", "message": f"Emir gönderildi: {action}"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
