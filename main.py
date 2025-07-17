from flask import Flask, request
import os
import redis
import json
import requests
import time

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

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

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return "ignored"

    msg = data["message"]
    text = msg.get("text") or msg.get("caption") or ""
    if not text:
        return "no text"

    # 🔥 رد خاص على نداء ملك التريكس
    if "مين ملك التريكس" in text:
        send_message("👑 أبو عبدو 🌹")

    # 🚨 إذا فيها قنص نبدأ مراقبة العملة
    if "تم قنص" in text:
        for word in text.split():
            if "-EUR" in word and not r.exists(word):
                price = fetch_price(word)
                if price:
                    r.set(word, json.dumps({
                        "entry": price,
                        "status": None,
                        "start_time": time.time()
                    }))
                    send_message(f"🕵️‍♂️ أبو الهول يراقب {word} عند {price} EUR")

    return "ok"

@app.route("/")
def home():
    return "🤖 Webhook ready for Abu Houl."
