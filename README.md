# Binarium Screenshot Telegram Analyzer

Простой режим: бот НЕ получает график в реальном времени и НЕ подключается к Binarium WebSocket.

Пользователь отправляет скриншот графика в Telegram → бот отправляет изображение в vision-модель → возвращает анализ на русском.

## Render

Build Command:
`pip install -r requirements.txt`

Start Command:
`python bot.py`

Health Check Path:
`/healthz`

Environment Variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (необязательно; по умолчанию `gpt-5.6-luna`)

Важно: API-ключ OpenAI хранится только в Render Environment Variables. Не вставляйте его в GitHub и не отправляйте его в чат.

Результат является модельным анализом изображения, а не гарантией результата сделки и не статистически подтвержденной вероятностью выигрыша.
