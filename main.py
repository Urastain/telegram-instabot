import os
import logging
import threading
import asyncio
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
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь ссылку на Instagram-видео.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    if "instagram.com" in message:
        await update.message.reply_text("Обработка ссылки… (скачивание пока не реализовано)")
        # Здесь вставьте ваш код скачивания видео
    else:
        await update.message.reply_text("Пожалуйста, отправь ссылку на Instagram.")

async def main():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Telegram приложение инициализировано")
    await application.run_polling()

# Healthcheck endpoint для Render — чтобы не засыпало приложение
@app.route("/")
def index():
    return "OK", 200

# "Keep alive" пингует сервер раз в 5 минут, чтобы Render не засыпал на бесплатном тарифе
def keep_alive():
    while True:
        try:
            requests.get(APP_URL)
        except Exception as e:
            logger.error(f"Keep alive ping failed: {e}")
        time.sleep(300)  # 5 минут

if __name__ == "__main__":
    # Запуск Telegram-бота polling в фоне
    threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()
    # Keep alive пинг (только если приложение реально доступно извне)
    if APP_URL != "http://localhost:10000":
        threading.Thread(target=keep_alive, daemon=True).start()
    # Flask healthcheck
    app.run(host="0.0.0.0", port=PORT)
