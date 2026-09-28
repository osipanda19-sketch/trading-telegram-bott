import os, time, threading, requests
from flask import Flask, jsonify

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
PORT = int(os.getenv("PORT", "10000"))
app = Flask(__name__)
BASE = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""

@app.get("/")
def home():
    return "Trading Telegram Bot is running."

@app.get("/healthz")
def healthz():
    return jsonify({"status":"ok","telegram_token_configured":bool(TOKEN)})

def tg(method, data=None, timeout=30):
    if not TOKEN:
        return {"ok":False,"description":"TELEGRAM_BOT_TOKEN is not configured"}
    try:
        return requests.post(f"{BASE}/{method}", json=data or {}, timeout=timeout).json()
    except Exception as e:
        return {"ok":False,"description":str(e)}

def send(chat_id, text):
    tg("sendMessage", {"chat_id":chat_id, "text":text})

def handle(message):
    cid = str(message["chat"]["id"])
    text = (message.get("text") or "").strip()
    if text.startswith("/start"):
        send(cid, "🤖 Бот запущен!\n\n/start — запуск\n/help — помощь\n/ping — проверка связи\n/id — показать Chat ID\n/status — статус")
    elif text.startswith("/help"):
        send(cid, "Бот готов. Следующий этап — подключение анализатора рынка.")
    elif text.startswith("/ping"):
        send(cid, "🏓 Pong! Связь работает.")
    elif text.startswith("/id"):
        send(cid, f"🆔 Ваш Chat ID: {cid}")
    elif text.startswith("/status"):
        send(cid, f"🟢 Бот онлайн.\nTELEGRAM_CHAT_ID настроен: {'да' if CHAT_ID else 'нет'}")

def poll():
    offset = None
    tg("deleteWebhook", {"drop_pending_updates":False})
    print("Telegram polling started.")
    while True:
        try:
            data = {"timeout":25, "allowed_updates":["message"]}
            if offset is not None: data["offset"] = offset
            r = tg("getUpdates", data, timeout=35)
            if not r.get("ok"):
                print("Telegram error:", r.get("description")); time.sleep(5); continue
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                if "message" in u:
                    try: handle(u["message"])
                    except Exception as e: print("Handler error:", e)
        except Exception as e:
            print("Polling error:", e); time.sleep(5)

if __name__ == "__main__":
    if TOKEN:
        threading.Thread(target=poll, daemon=True).start()
    else:
        print("ERROR: TELEGRAM_BOT_TOKEN is not configured.")
    app.run(host="0.0.0.0", port=PORT)
