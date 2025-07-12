import os
import time
import requests
from datetime import datetime, timedelta

# بيانات البيئة من Railway (مخزنة في Secrets)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not all([API_KEY, API_SECRET, BOT_TOKEN, CHAT_ID]):
    raise Exception("❌ تأكد من إدخال API_KEY و API_SECRET و BOT_TOKEN و CHAT_ID في إعدادات Secrets")

# روابط تيليغرام
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
GET_UPDATES_URL = f"{BASE_URL}/getUpdates"
SEND_MSG_URL = f"{BASE_URL}/sendMessage"

# بيانات الصفقة
active_trade = None

# إرسال رسالة إلى تيليغرام
def send_message(text):
    requests.post(SEND_MSG_URL, data={"chat_id": CHAT_ID, "text": text})

# شراء عملة
def buy_coin(symbol):
    url = "https://api.bitvavo.com/v2/order"
    headers = {
        "Bitvavo-Access-Key": API_KEY,
        "Bitvavo-Access-Signature": "",
        "Bitvavo-Access-Timestamp": "",
        "Bitvavo-Access-Window": "10000",
        "Content-Type": "application/json"
    }
    data = {
        "market": f"{symbol}-EUR",
        "side": "buy",
        "orderType": "market",
        "amount": "10"  # 10 يورو
    }
    # تنبيه: يجب إضافة توقيع ومؤقت حقيقيين (للاستخدام الحقيقي)
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# مراقبة البيع بعد الشراء
def monitor_trade(symbol, entry_price):
    global active_trade
    highest_price = entry_price
    start_time = datetime.utcnow()
    send_message(f"⏱ بدء المراقبة لـ {symbol} بعد الشراء بسعر {entry_price} EUR")

    while True:
        time.sleep(30)
        try:
            url = f"https://api.bitvavo.com/v2/market/{symbol}-EUR/ticker/price"
            price = float(requests.get(url).json()["price"])
            highest_price = max(highest_price, price)
            elapsed = datetime.utcnow() - start_time

            profit = (price - entry_price) / entry_price * 100
            drop_from_top = (price - highest_price) / highest_price * 100

            if profit >= 4:
                send_message(f"✅ بيع {symbol} بربح 4%: السعر {price} EUR")
                break
            elif profit <= -2.5:
                send_message(f"🚨 بيع {symbol} بخسارة -2.5%: السعر {price} EUR")
                break
            elif drop_from_top <= -2:
                send_message(f"📉 تم تفعيل Trailing Stop لـ {symbol}: السعر {price} EUR")
                break
            elif elapsed > timedelta(minutes=15):
                send_message(f"⌛️ بيع {symbol} بعد مرور 15 دقيقة: السعر {price} EUR")
                break
        except Exception as e:
            send_message(f"⚠️ خطأ أثناء مراقبة {symbol}: {e}")
            break

    active_trade = None

# قراءة رسائل تيليغرام
def get_last_message():
    try:
        res = requests.get(GET_UPDATES_URL).json()
        messages = res.get("result", [])
        if messages:
            return messages[-1]["message"]["text"]
    except:
        return None

# الحلقة الرئيسية
def main():
    global active_trade
    send_message("🤖 بوت أبو الهول يعمل الآن ويراقب إشارات القنص...")

    last_text = ""

    while True:
        try:
            text = get_last_message()
            if text and text != last_text and "تم قنص عملة" in text:
                last_text = text
                symbol = text.split("عملة")[-1].strip().upper()
                if not active_trade:
                    send_message(f"🛒 تم استلام إشارة لشراء {symbol}")
                    buy_response = buy_coin(symbol)
                    entry_price = float(buy_response.get("fills", [{}])[0].get("price", 0))
                    if entry_price > 0:
                        active_trade = symbol
                        monitor_trade(symbol, entry_price)
                    else:
                        send_message("❌ فشل في تنفيذ الشراء أو لم يتم جلب السعر.")
        except Exception as e:
            send_message(f"⚠️ خطأ: {e}")
        time.sleep(10)

if __name__ == "__main__":
    main()
