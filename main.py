import os
import time
import requests
from bitvavo import Bitvavo
from datetime import datetime, timedelta

# تحميل متغيرات البيئة من Railway
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# التأكد من أن كل المتغيرات موجودة
if not all([API_KEY, API_SECRET, BOT_TOKEN, CHAT_ID]):
    raise Exception("❌ تأكد من إدخال API_KEY و API_SECRET و BOT_TOKEN و CHAT_ID في Secrets")

# تهيئة مكتبة Bitvavo
bitvavo = Bitvavo({
  'APIKEY': API_KEY,
  'APISECRET': API_SECRET,
  'RESTURL': 'https://api.bitvavo.com/v2',
  'WSURL': 'wss://ws.bitvavo.com/v2/',
  'ACCESSWINDOW': 10000,
  'DEBUGGING': False
})

# روابط تيليغرام
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
GET_UPDATES_URL = f"{BASE_URL}/getUpdates"
SEND_MSG_URL = f"{BASE_URL}/sendMessage"

active_trade = None

# إرسال رسالة إلى تيليغرام
def send_message(text):
    requests.post(SEND_MSG_URL, data={"chat_id": CHAT_ID, "text": text})

# شراء عملة
def buy_coin(symbol):
    try:
        response = bitvavo.placeOrder(
            symbol + "-EUR",
            'buy',
            'market',
            { 'amount': '10' }  # شراء بـ 10 يورو
        )
        return response
    except Exception as e:
        send_message(f"❌ فشل في تنفيذ أمر الشراء: {e}")
        return None

# جلب سعر العملة الحالي
def get_price(symbol):
    try:
        ticker = bitvavo.tickerPrice(symbol + "-EUR")
        return float(ticker["price"])
    except:
        return None

# مراقبة البيع
def monitor_trade(symbol, entry_price):
    global active_trade
    highest_price = entry_price
    start_time = datetime.utcnow()

    send_message(f"⏱ بدء المراقبة لـ {symbol} بعد الشراء بسعر {entry_price} EUR")

    while True:
        time.sleep(30)
        price = get_price(symbol)
        if not price:
            send_message("⚠️ تعذر جلب السعر الحالي.")
            break

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
            send_message(f"📉 تفعيل Trailing Stop لـ {symbol}: السعر {price} EUR")
            break
        elif elapsed > timedelta(minutes=15):
            send_message(f"⌛️ بيع {symbol} بعد مرور 15 دقيقة: السعر {price} EUR")
            break

    active_trade = None

# جلب آخر رسالة تيليغرام
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
    send_message("🤖 بوت أبو الهول يعمل الآن... في انتظار إشارة 'تم قنص'.")

    last_text = ""

    while True:
        try:
            text = get_last_message()
            if text and text != last_text and "تم قنص عملة" in text:
                last_text = text
                symbol = text.split("عملة")[-1].strip().upper()
                if not active_trade:
                    send_message(f"🛒 تنفيذ شراء {symbol}...")
                    buy_response = buy_coin(symbol)
                    if buy_response and "fills" in buy_response and len(buy_response["fills"]) > 0:
                        entry_price = float(buy_response["fills"][0]["price"])
                        active_trade = symbol
                        monitor_trade(symbol, entry_price)
                    else:
                        send_message("⚠️ لم يتم العثور على بيانات السعر بعد الشراء.")
        except Exception as e:
            send_message(f"⚠️ خطأ: {e}")
        time.sleep(10)

if __name__ == "__main__":
    main()
