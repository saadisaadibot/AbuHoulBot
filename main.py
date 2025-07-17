import os
import time
import requests
import redis
import json

# تيليغرام
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Redis
redis_url = os.getenv("REDIS_URL")
r = redis.from_url(redis_url, decode_responses=True)

def send_message(text):
    requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": CHAT_ID, "text": text})

def fetch_price(symbol):
    try:
        url = f"https://api.bitvavo.com/v2/ticker/price?market={symbol}"
        response = requests.get(url)
        if response.status_code == 200:
            return float(response.json()["price"])
    except:
        return None

def delete_memory():
    r.flushdb()
    send_message("🧹 تم مسح ذاكرة أبو الهول بالكامل.")

def check_prices():
    for symbol in r.keys():
        if symbol == "sell_log":
            continue

        entry = json.loads(r.get(symbol))
        current = fetch_price(symbol)
        if not current:
            continue

        entry_price = entry["entry"]

        if entry.get("status") == "trailing":
            peak = entry["peak"]
            if current > peak:
                entry["peak"] = current
                r.set(symbol, json.dumps(entry))

            drop = ((peak - current) / peak) * 100
            if drop >= 1.5:
                change = ((current - entry_price) / entry_price) * 100
                send_message(f"🎯 {symbol} تم البيع بعد ارتفاع ثم نزول – ربح {round(change,2)}%")
                log = json.loads(r.get("sell_log") or "[]")
                log.append({
                    "symbol": symbol,
                    "entry": entry_price,
                    "exit": current,
                    "change": round(change,2),
                    "result": "ربح"
                })
                r.set("sell_log", json.dumps(log))
                r.delete(symbol)
        else:
            change = ((current - entry_price) / entry_price) * 100
            if change >= 3:
                entry["status"] = "trailing"
                entry["peak"] = current
                entry["start_time"] = time.time()
                r.set(symbol, json.dumps(entry))
                send_message(f"🟢 {symbol} ارتفعت +3% – نبدأ مراقبة القمة.")
            elif change <= -3:
                send_message(f"📉 {symbol} خسارة -{round(abs(change), 2)}% – تم البيع.")
                log = json.loads(r.get("sell_log") or "[]")
                log.append({
                    "symbol": symbol,
                    "entry": entry_price,
                    "exit": current,
                    "change": round(change,2),
                    "result": "خسارة"
                })
                r.set("sell_log", json.dumps(log))
                r.delete(symbol)

def get_updates(offset=None):
    res = requests.get(f"{BASE_URL}/getUpdates", params={"offset": offset, "timeout": 10})
    return res.json()

def format_duration(minutes):
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours} ساعة و{mins} دقيقة"
    else:
        return f"{mins} دقيقة"

def handle_command(text):
    if "احذف" in text or "حذف" in text:
        delete_memory()

    elif "الملخص" in text or "الحسابات" in text:
        log = json.loads(r.get("sell_log") or "[]")
        if not log:
            send_message("📊 لا توجد أي عمليات بيع مُسجلة بعد.")
        else:
            total_profit = 0
            win_count = 0
            lose_count = 0
            for trade in log:
                entry = trade["entry"]
                exit_price = trade["exit"]
                profit_percent = ((exit_price - entry) / entry) * 100
                total_profit += profit_percent
                if profit_percent >= 0:
                    win_count += 1
                else:
                    lose_count += 1

            msg = (
                f"📈 عدد الصفقات الرابحة: {win_count}\n"
                f"📉 عدد الصفقات الخاسرة: {lose_count}\n"
                f"💰 صافي الربح/الخسارة: {round(total_profit, 2)}%\n"
            )

            watchlist = []
            for key in r.keys():
                if key == "sell_log":
                    continue
                entry = json.loads(r.get(key))
                duration_min = int((time.time() - entry["start_time"]) / 60)
                watchlist.append(f"- {key} منذ {format_duration(duration_min)}")

            if watchlist:
                msg += "\n👁️ العملات التي تتم مراقبتها الآن:\n" + "\n".join(watchlist)

            send_message(msg)

def detect_snipe_messages(text):
    if "تم قنص" in text:
        parts = text.split()
        for word in parts:
            if "-EUR" in word and not r.exists(word):
                price = fetch_price(word)
                if price:
                    r.set(word, json.dumps({
                        "entry": price,
                        "status": None,
                        "start_time": time.time()
                    }))
                    send_message(f"🕵️‍♂️ أبو الهول يراقب {word} عند {price} EUR")

send_message("🤖 تم تشغيل أبو الهول بنسخة Railway.")
offset = None
last_cycle = time.time()

while True:
    try:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message") or update.get("edited_message")
            if not msg:
                continue
            text = msg.get("text") or msg.get("caption") or ""
            if not text:
                continue
                # رد تلقائي على "مين ملك التريكس"
if "مين ملك التريكس" in text:
    send_message("أبو عبدو 👑🌹🌹🌹")
    continue
            handle_command(text)
            detect_snipe_messages(text)

        check_prices()
        time.sleep(5)

    except Exception as e:
        print(f"❌ خطأ: {e}")
        time.sleep(10)
