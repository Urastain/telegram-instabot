import os
import logging
import threading
import time
import requests
import asyncio

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
APP_URL = os.environ.get("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь ссылку на Instagram-видео.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()
    if "instagram.com" in message:
        await update.message.reply_text("Скачиваю видео…")
        try:
            filename = f"video_{update.message.message_id}.mp4"
            ydl_opts = {
                'outtmpl': filename,
                'format': 'mp4',
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([message])
            # Отправить видео пользователю
            with open(filename, "rb") as video:
                await update.message.reply_video(video)
            os.remove(filename)
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            await update.message.reply_text(f"Ошибка скачивания: {e}")
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
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Telegram приложение инициализировано")
    asyncio.run(application.run_polling())
