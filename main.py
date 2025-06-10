import os
import logging
import threading
import time
import requests

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
APP_URL = os.environ.get("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь ссылку на Instagram-видео.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    if "instagram.com" in message:
        await update.message.reply_text("Обработка ссылки… (скачивание пока не реализовано)")
    else:
        await update.message.reply_text("Пожалуйста, отправь ссылку на Instagram.")

@app.route("/")
def index():
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

def keep_alive():
    while True:
        try:
            requests.get(APP_URL)
        except Exception as e:
            logger.error(f"Keep alive ping failed: {e}")
        time.sleep(300)  # 5 минут

if __name__ == "__main__":
    # Запуск Flask и keep_alive в отдельных потоках
    threading.Thread(target=run_flask, daemon=True).start()
    if APP_URL != "http://localhost:10000":
        threading.Thread(target=keep_alive, daemon=True).start()

    # Telegram polling — в главном потоке!
    from telegram.ext import Application
    import asyncio

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("Telegram приложение инициализировано")
    asyncio.run(application.run_polling())
