from flask import Flask, request
from binance.client import Client
import json
import os

app = Flask(__name__)

# Başlangıç loglaması
print("Uygulama başlatılıyor...")

# Binance API anahtarlarını ortam değişkenlerinden al
binance_api_key = os.getenv("BINANCE_API_KEY", "YOUR_API_KEY")
binance_api_secret = os.getenv("BINANCE_API_SECRET", "YOUR_API_SECRET")
print(f"API Key: {binance_api_key[:5]}... (gizlilik için kısaltıldı)")
print(f"API Secret: {binance_api_secret[:5]}... (gizlilik için kısaltıldı)")

# Testnet için client'ı başlat
try:
    print("Binance client başlatılıyor...")
    client = Client(binance_api_key, binance_api_secret, testnet=True)
    print("Binance client başarıyla başlatıldı.")
    # Hedge Mode'u etkinleştir (hata olsa bile uygulama çökmesin)
    try:
        client.futures_change_position_mode(dualSidePosition=True)
        print("Hedge Mode etkinleştirildi.")
    except Exception as e:
        print(f"Hedge Mode ayarı yapılamadı: {str(e)}")
except Exception as e:
    print(f"Binance client başlatılamadı: {str(e)}")
    raise  # Hatayı loglara yaz ve uygulamayı çökert

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()  # JSON verisini al
        if not data:
            return {"status": "error", "message": "No JSON data received"}, 400

        action = data.get('action')  # buy, sell, close_all
        symbol = data.get('symbol', "BTCUSDT")
        quantity = float(data.get('quantity', 0))
        label = data.get('label', "")
        kademe = int(data.get('kademe', 0))
        reason = data.get('reason', "")

        print(f"Webhook alındı: action={action}, symbol={symbol}, quantity={quantity}")

        # USDT miktarını coin miktarına çevir
        price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        coin_quantity = round(quantity / price, 3)

        # Bakiye kontrolü
        balance = float(client.futures_account()['availableBalance'])
        if action in ['buy', 'sell'] and quantity > balance:
            raise Exception(f"Yetersiz bakiye: Gerekli {quantity} USDT, Mevcut {balance} USDT")

        if action == 'buy':
            order = client.futures_create_order(
                symbol=symbol,
                side=Client.SIDE_BUY,
                positionSide="LONG",
                type=Client.ORDER_TYPE_MARKET,
                quantity=coin_quantity
            )
            print(f"Long pozisyon açıldı: {label}, Miktar: {coin_quantity}, Kademe: {kademe}")
        
        elif action == 'sell':
            order = client.futures_create_order(
                symbol=symbol,
                side=Client.SIDE_SELL,
                positionSide="SHORT",
                type=Client.ORDER_TYPE_MARKET,
                quantity=coin_quantity
            )
            print(f"Short pozisyon açıldı: {label}, Miktar: {coin_quantity}, Kademe: {kademe}")
        
        elif action == 'close_all':
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
        print(f"Webhook işlenirken hata: {str(e)}")
        return {"status": "error", "message": str(e)}, 400

@app.route('/')
def health_check():
    return {"status": "success", "message": "Uygulama çalışıyor!"}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Sunucu {port} portunda başlatılıyor...")
    app.run(host='0.0.0.0', port=port)
