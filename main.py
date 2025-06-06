import os
import re
import logging
import asyncio
import instaloader
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- Настройка логирования ---
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Переменные окружения ---
TOKEN = os.getenv("BOT_TOKEN")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# --- Регулярное выражение для Instagram ---
INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(\?.*)?"

# --- Класс загрузки видео ---
class InstagramDownloader:
    def __init__(self):
        self.L = instaloader.Instaloader(download_pictures=False, quiet=True)

    async def download_video(self, shortcode):
        try:
            post = instaloader.Post.from_shortcode(self.L.context, shortcode)
            if not post.is_video:
                return None, "❌ Это не видео."

            video_url = post.video_url
            response = await asyncio.get_event_loop().run_in_executor(None, requests.get, video_url)
            content_length = int(response.headers.get('Content-Length', 0))
            if content_length > MAX_FILE_SIZE:
                return None, "❌ Видео слишком большое (>50MB)."

            temp_file = f"{shortcode}.mp4"
            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            return temp_file, None
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            return None, f"❌ Ошибка загрузки: {str(e)}"

# --- Обработчик сообщений ---
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    if not re.search(INSTAGRAM_REGEX, message.text):
        return

    logger.info(f"Получена ссылка: {message.text}")

    shortcode = message.text.split("/")[-2]
    downloader = InstagramDownloader()
    temp_file, error = await downloader.download_video(shortcode)

    if error:
        logger.error(error)
        await message.reply_text(error)
        return

    try:
        await chat.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    try:
        with open(temp_file, "rb") as video:
            await chat.send_video(video=video, supports_streaming=True)
    except Exception as e:
        logger.error(f"Ошибка отправки видео: {e}")
        await message.reply_text("❌ Ошибка отправки видео.")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# --- Основной запуск бота ---
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Regex(INSTAGRAM_REGEX), handle_instagram))
    logger.info("🤖 Бот запущен")
    await app.run_polling()

# --- Бесконечный перезапуск бота ---
def run_bot():
    while True:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Ошибка работы бота: {e}")
            logger.info("Перезапуск бота через 10 секунд...")
            loop.run_until_complete(asyncio.sleep(10))

if __name__ == "__main__":
    run_bot()
