from flask import Flask, request, jsonify
import ccxt
import os

app = Flask(__name__)

# Binance API kimlik bilgileri (environment variables ile)
binance_api_key = os.getenv("BINANCE_API_KEY", "YOUR_API_KEY")
binance_api_secret = os.getenv("BINANCE_API_SECRET", "YOUR_API_SECRET")

exchange = ccxt.binance({
    'apiKey': binance_api_key,
    'secret': binance_api_secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'  # Futures için
    }
})

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Ham veriyi al ve JSON’a dönüştür (Content-Type kontrolü olmadan)
        data = request.get_data().decode('utf-8')
        webhook_data = json.loads(data)

        action = webhook_data.get('action')
        symbol = webhook_data.get('symbol')
        quantity = float(webhook_data.get('quantity', 0))
        label = webhook_data.get('label')
        kademe = webhook_data.get('kademe')
        reason = webhook_data.get('reason')

        print(f"Webhook alındı: action={action}, symbol={symbol}, quantity={quantity}")

        if action == "buy":
            order = exchange.create_market_buy_order(symbol, quantity)
            print(f"Buy order placed: {order}")
        elif action == "sell":
            order = exchange.create_market_sell_order(symbol, quantity)
            print(f"Sell order placed: {order}")
        elif action == "close_all":
            positions = exchange.fetch_positions([symbol])
            for position in positions:
                if position['info']['positionAmt'] != '0':
                    if float(position['info']['positionAmt']) > 0:
                        exchange.create_market_sell_order(symbol, abs(float(position['info']['positionAmt'])))
                    else:
                        exchange.create_market_buy_order(symbol, abs(float(position['info']['positionAmt'])))
            print(f"All positions closed for {symbol}")

        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Webhook işlenirken hata: {str(e)}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
