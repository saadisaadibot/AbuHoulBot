from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = "8009488976:AAGU5x04wCdDavSoxzEM77SF17ZB_6QP-wU"

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat = data["message"]["chat"]
        chat_id = chat.get("id")
        username = chat.get("username", "بدون اسم مستخدم")
        print(f"✅ Chat ID: {chat_id} | Username: {username}")
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
