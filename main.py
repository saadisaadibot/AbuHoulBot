import os
import time
import requests
from datetime import datetime, timedelta

# مفاتيح البيئة
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# تخزين الصفقات المفتوحة
active_trades = {}

# إرسال رسالة إلى تيليغرام
def send_message(text):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data)

# تنفيذ أمر شراء من Bitvavo
def place_order(symbol, amount_eur):
    url = "https://api.bitvavo.com/v2/order"
    headers = {
        "Bitvavo-Access-Key": API_KEY,
        "Bitvavo-Access-Signature": "",
        "Bitvavo-Access-Timestamp": str(int(time.time() * 1000)),
        "Bitvavo-Access-Window": "10000"
    }
    data = {
        "market": symbol,
        "side": "buy",
        "orderType": "market",
        "amount": str(amount_eur)
    }
    # يتم تنفيذ الطلب لاحقًا عبر مكتبة موقعة أو HTTP مباشر إذا أردت

# جلب السعر الحالي للعملة
def get_price(symbol):
    try:
        url = f"https://api.bitvavo.com/v2/ticker/price"
        response = requests.get(url)
        if response.status_code == 200:
            prices = response.json()
            for item in prices:
                if item["market"] == symbol:
                    return float(item["price"])
    except:
        return None

# جلب رسائل تيليغرام
def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 10, "offset": offset}
    try:
        res = requests.get(url, params=params)
        return res.json()
    except:
        return {}

# التحقق من شروط البيع
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
            send_message(f"💥 تم البيع الإجباري لـ {symbol} بخسارة -2%")
            to_remove.append(symbol)

        elif change >= 4 and drop_from_peak >= 1.5:
            send_message(f"✅ تم البيع بربح بعد التريلينغ لـ {symbol} 💰")
            to_remove.append(symbol)

        elif elapsed >= 1800:  # 30 دقيقة
            send_message(f"⏱️ تم البيع النهائي لـ {symbol} بعد مرور 30 دقيقة")
            to_remove.append(symbol)

    for symbol in to_remove:
        active_trades.pop(symbol, None)

# بدء السكربت
def main():
    send_message("🤖 تم تشغيل بوت أبو الهول للتنفيذ التلقائي...")
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

                        price = get_price(symbol)
                        if not price:
                            send_message(f"⚠️ لم أتمكن من جلب سعر {symbol}")
                            continue

                        active_trades[symbol] = {
                            "buy_price": price,
                            "max_price": price,
                            "buy_time": datetime.utcnow()
                        }
                        send_message(f"🛒 تم تنفيذ شراء {symbol} على السعر {price} EUR")
                        # place_order(symbol, 10) ← جاهزة للتنفيذ الفعلي

        check_sell_conditions()
        time.sleep(10)

main()
