import os
import re
import logging
import requests
import threading
import time

from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (лучше хранить в переменных окружения!)
TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")

# Регулярное выражение для ссылок Instagram
INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(\?.*)?"

# Flask для keep-alive (Render)
app = Flask(__name__)

@app.route('/')
def index():
    return 'OK', 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        return
    while True:
        try:
            requests.get(url)
        except Exception as e:
            logger.warning(f"Keep-alive failed: {e}")
        time.sleep(300)

async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    if not re.search(INSTAGRAM_REGEX, message.text):
        return

    logger.info(f"Получена ссылка: {message.text}")

    shortcode = message.text.split("/")[-2]
    temp_file = f"{shortcode}.mp4"

    try:
        import instaloader
        L = instaloader.Instaloader(download_pictures=False, quiet=True)
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        if not post.is_video:
            logger.warning("Пост не является видео")
            await chat.send_message("Это не видеопост или видео недоступно.")
            return

        video_url = post.video_url
        response = requests.get(video_url, stream=True, timeout=30)
        response.raise_for_status()

        content_length = int(response.headers.get('Content-Length', 0))
        if content_length > 50 * 1024 * 1024:
            logger.warning("Видео слишком большое")
            await chat.send_message("Видео слишком большое (>50MB) для отправки.")
            return

        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        with open(temp_file, 'rb') as video_file:
            await chat.send_video(video=video_file,
                                  caption="📥 Видео из Instagram",
                                  supports_streaming=True)

        try:
            await context.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
            logger.info("Сообщение успешно удалено")
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение: {e}")

    except Exception as e:
        logger.error(f"Ошибка обработки видео: {e}")
        await chat.send_message(f"Ошибка обработки: {e}")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()

    app_tg = ApplicationBuilder().token(TOKEN).build()
    app_tg.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(INSTAGRAM_REGEX),
                       handle_instagram_link)
    )

    logger.info("🤖 Бот запущен")
    app_tg.run_polling()

if __name__ == "__main__":
    main()
