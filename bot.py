import os, time, threading, sqlite3
from flask import Flask, jsonify, request
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
QUOTE_KEY = os.getenv("QUOTE_INGEST_KEY", "").strip()
PORT = int(os.getenv("PORT", "10000"))
DB_PATH = os.getenv("DB_PATH", "quotes.db")

app = Flask(__name__)
TG = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS quotes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        asset TEXT NOT NULL,
        price REAL NOT NULL
    )""")
    c.commit()
    c.close()

def tg(method, data=None, timeout=20):
    if not TOKEN:
        return {"ok": False, "description": "TELEGRAM_BOT_TOKEN not configured"}
    try:
        return requests.post(f"{TG}/{method}", json=data or {}, timeout=timeout).json()
    except Exception as e:
        return {"ok": False, "description": str(e)}

def send(chat_id, text):
    return tg("sendMessage", {"chat_id": chat_id, "text": text})

@app.get("/")
def home():
    return "Trading Telegram Bot + Binarium Bridge is running."

@app.get("/healthz")
def healthz():
    return jsonify(ok=True, quote_key_configured=bool(QUOTE_KEY))

@app.get("/api/status")
def status():
    c = db()
    r = c.execute("SELECT ts, asset, price FROM quotes ORDER BY id DESC LIMIT 1").fetchone()
    count = c.execute("SELECT COUNT(*) AS n FROM quotes").fetchone()["n"]
    c.close()
    return jsonify(online=True, quotes=count, last_quote=dict(r) if r else None)

@app.post("/api/quote")
def quote():
    if not QUOTE_KEY or request.headers.get("X-API-Key") != QUOTE_KEY:
        return jsonify(error="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    try:
        asset = str(data["asset"])
        price = float(data["price"])
        ts = str(data.get("ts") or "")
    except (KeyError, TypeError, ValueError):
        return jsonify(error="bad quote payload"), 400

    c = db()
    c.execute("INSERT INTO quotes(ts,asset,price) VALUES(?,?,?)",
              (ts, asset, price))
    c.commit()
    c.close()
    return jsonify(ok=True)

def handle(message):
    cid = str(message["chat"]["id"])
    text = (message.get("text") or "").strip()
    if text.startswith("/start"):
        send(cid, "🤖 Бот запущен!\n\n/start — запуск\n/help — помощь\n/ping — проверка связи\n/id — Chat ID\n/status — статус\n/quotes — последние котировки")
    elif text.startswith("/help"):
        send(cid, "Бот принимает котировки через READ ONLY Bridge. Заявки на сделки он не отправляет.")
    elif text.startswith("/ping"):
        send(cid, "🏓 Pong! Связь работает.")
    elif text.startswith("/id"):
        send(cid, f"🆔 Ваш Chat ID: {cid}")
    elif text.startswith("/status"):
        c = db()
        r = c.execute("SELECT ts,asset,price FROM quotes ORDER BY id DESC LIMIT 1").fetchone()
        n = c.execute("SELECT COUNT(*) AS n FROM quotes").fetchone()["n"]
        c.close()
        last = f"{r['asset']} {r['price']} ({r['ts']})" if r else "пока нет"
        send(cid, f"🟢 Бот онлайн.\nКотировок получено: {n}\nПоследняя: {last}")
    elif text.startswith("/quotes"):
        c = db()
        rows = c.execute("SELECT ts,asset,price FROM quotes ORDER BY id DESC LIMIT 5").fetchall()
        c.close()
        if not rows:
            send(cid, "Пока котировок нет.")
        else:
            send(cid, "📊 Последние котировки:\n" + "\n".join(
                f"{r['asset']}: {r['price']} — {r['ts']}" for r in rows
            ))

def poll():
    offset = None
    tg("deleteWebhook", {"drop_pending_updates": False})
    print("Telegram polling started.")
    while True:
        try:
            payload = {"timeout": 25, "allowed_updates": ["message"]}
            if offset is not None:
                payload["offset"] = offset
            res = tg("getUpdates", payload, timeout=35)
            if not res.get("ok"):
                print("Telegram error:", res.get("description"))
                time.sleep(5)
                continue
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                if "message" in u:
                    try:
                        handle(u["message"])
                    except Exception as e:
                        print("Handler error:", e)
        except Exception as e:
            print("Polling error:", e)
            time.sleep(5)

init_db()

if __name__ == "__main__":
    if TOKEN:
        threading.Thread(target=poll, daemon=True).start()
    else:
        print("ERROR: TELEGRAM_BOT_TOKEN is not configured.")
    app.run(host="0.0.0.0", port=PORT)
