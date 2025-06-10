import os
import logging

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь ссылку на Instagram-видео.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    if "instagram.com" in message:
        await update.message.reply_text("Обработка ссылки… (пока не реализовано)")
    else:
        await update.message.reply_text("Пожалуйста, отправь ссылку на Instagram.")

async def main():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Telegram приложение инициализировано")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    import threading

    # Запуск Telegram-бота в отдельном потоке (polling)
    threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()

    # Flask-приложение (например, healthcheck)
    @app.route("/")
    def index():
        return "OK", 200

    app.run(host="0.0.0.0", port=10000)
