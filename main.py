import os
import time
import requests
from datetime import datetime, timedelta
from bitvavo import Bitvavo

# إعداد Bitvavo
bitvavo = Bitvavo({
    'APIKEY': os.getenv("API_KEY"),
    'APISECRET': os.getenv("API_SECRET"),
    'RESTURL': 'https://api.bitvavo.com/v2',
    'WSURL': 'wss://ws.bitvavo.com/v2/',
    'ACCESSWINDOW': 10000
})

# إعدادات تيليغرام
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# صفقات نشطة
active_trades = {}

# إرسال رسالة إلى تيليغرام
def send_message(text):
    try:
        url = f"{BASE_URL}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text}
        requests.post(url, data=data)
    except:
        pass

# شراء مباشر بـ 10 يورو
def place_buy(symbol):
    try:
        order = bitvavo.placeOrder(symbol, {
            'market': symbol,
            'side': 'buy',
            'orderType': 'market',
            'amount': '10',
            'paymentCurrency': 'EUR'
        })
        return float(order['fills'][0]['price']) if 'fills' in order and order['fills'] else None
    except Exception as e:
        send_message(f"⚠️ خطأ أثناء الشراء: {e}")
        return None

# بيع مباشر كل الكمية
def place_sell(symbol):
    try:
        balance = bitvavo.balance(symbol.replace("-EUR", "").upper())
        available = float(balance[0]['available'])
        if available > 0:
            bitvavo.placeOrder(symbol, {
                'market': symbol,
                'side': 'sell',
                'orderType': 'market',
                'amount': str(available)
            })
            send_message(f"💰 تم البيع الكامل لـ {symbol} بنجاح.")
    except Exception as e:
        send_message(f"⚠️ خطأ أثناء البيع: {e}")

# جلب السعر الحالي
def get_price(symbol):
    try:
        res = bitvavo.tickerPrice({'market': symbol})
        return float(res['price'])
    except:
        return None

# تحديث الصفقات ومراقبة البيع
def check_sell_conditions():
    now = datetime.utcnow()
    to_remove = []

    for symbol in list(active_trades.keys()):
        data = active_trades[symbol]
        current_price = get_price(symbol)
        if not current_price:
            continue

        buy_price = data["buy_price"]
        max_price = max(current_price, data["max_price"])
        active_trades[symbol]["max_price"] = max_price

        change = ((current_price - buy_price) / buy_price) * 100
        drop_from_peak = ((max_price - current_price) / max_price) * 100
        elapsed = (now - data["buy_time"]).total_seconds()

        if change <= -2:
            place_sell(symbol)
            send_message(f"❌ بيع بخسارة -2%: {symbol}")
            to_remove.append(symbol)

        elif change >= 4 and drop_from_peak >= 1.5:
            place_sell(symbol)
            send_message(f"✅ بيع بربح بعد تريلينغ: {symbol}")
            to_remove.append(symbol)

        elif elapsed >= 1800:
            place_sell(symbol)
            send_message(f"⏱️ بيع تلقائي بعد 30 دقيقة: {symbol}")
            to_remove.append(symbol)

    for symbol in to_remove:
        active_trades.pop(symbol, None)

# جلب تحديثات تيليغرام
def get_updates(offset=None):
    try:
        url = f"{BASE_URL}/getUpdates"
        params = {"timeout": 10, "offset": offset}
        response = requests.get(url, params=params)
        return response.json()
    except:
        return {}

# تشغيل البوت
def main():
    send_message("🤖 تم تشغيل أبو الهول للتنفيذ التلقائي على Bitvavo.")
    offset = None

    while True:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            if "message" in update:
                msg = update["message"].get("text", "")
                if "تم قنص" in msg:
                    parts = msg.split()
                    if len(parts) >= 4:
                        symbol = parts[3].upper().strip()
                        if not symbol.endswith("-EUR"):
                            symbol += "-EUR"

                        buy_price = place_buy(symbol)
                        if buy_price:
                            active_trades[symbol] = {
                                "buy_price": buy_price,
                                "max_price": buy_price,
                                "buy_time": datetime.utcnow()
                            }
                            send_message(f"🛒 تم شراء {symbol} على السعر {buy_price} EUR ✅")

        check_sell_conditions()
        time.sleep(10)

main()
