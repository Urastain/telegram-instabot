import os
import re
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import instaloader

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Регулярное выражение для Instagram
INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(\?.*)?"

# Класс для загрузки видео
class InstagramDownloader:
    def __init__(self):
        self.L = instaloader.Instaloader(download_pictures=False, quiet=True)

    async def download_video(self, shortcode):
        try:
            post = instaloader.Post.from_shortcode(self.L.context, shortcode)
            if not post.is_video:
                return None, "❌ Это не видео."
            video_url = post.video_url
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
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

# Обработчик сообщений
async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    if not re.search(INSTAGRAM_REGEX, message.text):
        return

    logger.info(f"Получена ссылка: {message.text}")

    shortcode = message.text.split("/")[-2]
    downloader = InstagramDownloader()
    temp_file, error = await asyncio.get_event_loop().run_in_executor(None, downloader.download_video, shortcode)

    if error:
        logger.error(error)
        return

    try:
        # Удаляем исходное сообщение
        await chat.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    try:
        # Отправляем видео
        with open(temp_file, "rb") as video:
            await chat.send_video(video=video, supports_streaming=True)
    except Exception as e:
        logger.error(f"Ошибка отправки видео: {e}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Функция запуска бота
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Regex(INSTAGRAM_REGEX), handle_instagram_link))
    logger.info("🤖 Бот запущен")
    await app.run_polling()

# Бесконечный цикл с перезапуском
def run_bot():
    loop = asyncio.new_event_loop()
    while True:
        try:
            loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Ошибка работы бота: {e}")
            logger.info("Перезапуск бота через 10 секунд...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(asyncio.sleep(10))

if __name__ == "__main__":
    run_bot()
