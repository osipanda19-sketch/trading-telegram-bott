import os
import base64
import io
import asyncio
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
PORT = int(os.getenv("PORT", "10000"))

app = Flask(__name__)

@app.get("/")
def home():
    return "Screenshot Trading Analyzer is running."

@app.get("/healthz")
def healthz():
    return jsonify(
        ok=True,
        telegram_configured=bool(TOKEN),
        openai_configured=bool(OPENAI_API_KEY),
    )

def analyze_image(image_bytes: bytes) -> str:
    if not OPENAI_API_KEY:
        return "❌ Не настроен OPENAI_API_KEY в Render."

    client = OpenAI(api_key=OPENAI_API_KEY)
    b64 = base64.b64encode(image_bytes).decode("ascii")

    prompt = """Ты анализируешь скриншот торгового графика только по информации, которая реально видна на изображении.

Ответь строго на русском и в таком формате:

📊 АНАЛИЗ ГРАФИКА
• Актив: ...
• Таймфрейм: ... (если виден; иначе «не виден»)
• Текущая цена: ... (если видна)
• Тренд: ВВЕРХ / ВНИЗ / БОКОВИК / НЕОПРЕДЕЛЁН
• Структура: ...
• Уровни поддержки/сопротивления: ...
• Свечная картина: ...
• Индикаторы: ... (только если реально видны)
• Ближайший сценарий: ...

🎯 МОДЕЛЬНЫЙ СИГНАЛ
Направление: ВВЕРХ / ВНИЗ / НЕ ОПРЕДЕЛЕНО
Экспирация: 1 мин / 2 мин / НЕ ОПРЕДЕЛЕНА
Модельная уверенность: X/100

⚠️ Риски: ...

Правила:
1. Не выдумывай значения индикаторов, цены, таймфрейм или уровни, которых не видно.
2. Если скриншот плохого качества или данных недостаточно, прямо напиши «НЕДОСТАТОЧНО ДАННЫХ».
3. «Модельная уверенность» — это оценка качества сигнала по изображению, а НЕ статистически подтверждённая вероятность выигрыша.
4. Не обещай прибыль и не утверждай, что сделка гарантированно выигрышная.
5. Для бинарных опционов отдельно отметь высокий риск.
6. Не отправляй заявку и не выполняй торговые действия.
"""

    response = client.responses.create(
        model=MODEL,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{b64}",
                },
            ],
        }],
    )
    return response.output_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бот анализа скриншотов готов.\n\n"
        "Просто отправь мне скриншот графика Binarium.\n"
        "Я проанализирую только изображение — без подключения к WebSocket и без получения котировок в реальном времени.\n\n"
        "/start — запуск\n"
        "/ping — проверка связи\n"
        "/status — статус"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Бот работает.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟢 Бот онлайн.\n"
        f"OpenAI API: {'настроен' if OPENAI_API_KEY else 'не настроен'}\n"
        f"Модель: {MODEL}\n"
        "Режим: анализ скриншота, без real-time котировок."
    )

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    status_msg = await msg.reply_text("🔎 Анализирую скриншот...")

    try:
        photo = msg.photo[-1]
        tg_file = await context.bot.get_file(photo.file_id)
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        result = await asyncio.to_thread(analyze_image, buf.getvalue())

        # Telegram message limit is 4096 chars.
        if len(result) <= 4000:
            await status_msg.edit_text(result)
        else:
            await status_msg.delete()
            for i in range(0, len(result), 4000):
                await msg.reply_text(result[i:i+4000])
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка анализа: {e}")

async def text_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправь именно фотографию/скриншот графика. "
        "Я не получаю поток котировок и не подключаюсь к Binarium."
    )

def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.PHOTO, photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_help))

    # Run Telegram long polling in the main process.
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
