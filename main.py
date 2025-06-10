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
import instaloader

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
APP_URL = os.environ.get("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь ссылку на Instagram-пост, и я попробую скачать видео без авторизации.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()
    if "instagram.com" in message:
        await update.message.reply_text("Пробую скачать видео через instaloader…")
        try:
            loader = instaloader.Instaloader(dirname_pattern=".", save_metadata=False, download_comments=False, download_video_thumbnails=False)
            shortcode = None
            # Попробуем вытащить shortcode из ссылки
            import re
            m = re.search(r"instagram\.com/(?:reel|p|tv)/([A-Za-z0-9_-]{5,})", message)
            if m:
                shortcode = m.group(1)
            else:
                await update.message.reply_text("Не удалось определить идентификатор видео.")
                return
            
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            if post.is_video:
                video_url = post.video_url
                filename = f"video_{update.message.message_id}.mp4"
                resp = requests.get(video_url)
                with open(filename, "wb") as f:
                    f.write(resp.content)
                with open(filename, "rb") as video:
                    await update.message.reply_video(video)
                os.remove(filename)
            else:
                await update.message.reply_text("Это не видео-пост или видео недоступно.")
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            await update.message.reply_text(f"Ошибка скачивания: {e}")
    else:
        await update.message.reply_text("Пожалуйста, отправь ссылку на пост Instagram.")

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
    threading.Thread(target=run_flask, daemon=True).start()
    if APP_URL != "http://localhost:10000":
        threading.Thread(target=keep_alive, daemon=True).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Telegram приложение инициализировано")
    import asyncio
    asyncio.run(application.run_polling())
