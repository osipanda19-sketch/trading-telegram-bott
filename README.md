# Trading Telegram Bot — Render Ready

Render:
- Build: `pip install -r requirements.txt`
- Start: `gunicorn --bind 0.0.0.0:$PORT bot:app`
- Health Check: `/healthz`

Environment variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Commands: `/start`, `/help`, `/ping`, `/id`, `/status`.

This bot is read-only and does not place trades.
