import os
import re
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import instaloader

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Переменные окружения ---
TOKEN = os.getenv("BOT_TOKEN")
INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(\?.*)?"

# --- Класс загрузки видео ---
class InstagramDownloader:
    def __init__(self):
        self.L = instaloader.Instaloader(download_pictures=False, quiet=True)

    def download_video(self, shortcode):
        try:
            post = instaloader.Post.from_shortcode(self.L.context, shortcode)
            if not post.is_video:
                return None
            video_url = post.video_url
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            temp_file = f"{shortcode}.mp4"
            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            return temp_file
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            return None

# --- Обработчик сообщений ---
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    if not re.search(INSTAGRAM_REGEX, message.text):
        return

    logger.info(f"Обнаружена ссылка: {message.text}")

    shortcode = message.text.split("/")[-2]
    downloader = InstagramDownloader()
    temp_file = downloader.download_video(shortcode)

    if not temp_file:
        await message.reply_text("❌ Не удалось скачать видео.")
        return

    try:
        await context.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    try:
        with open(temp_file, "rb") as video:
            await chat.send_video(video=video, supports_streaming=True)
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# --- Основной запуск бота ---
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Regex(INSTAGRAM_REGEX), handle_instagram))
    logger.info("🤖 Бот запущен")
    await app.run_polling()

# --- Бесконечный перезапуск ---
def run_bot():
    while True:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Ошибка работы бота: {e}")
            logger.info("Перезапуск бота через 10 секунд...")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
