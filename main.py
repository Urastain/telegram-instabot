import os
import re
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Регулярное выражение для ссылок Instagram
INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(\?.*)?"


async def handle_instagram_link(update: Update, context):
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
            return

        video_url = post.video_url
        response = requests.get(video_url, stream=True, timeout=30)
        response.raise_for_status()

        content_length = int(response.headers.get('Content-Length', 0))
        if content_length > 50 * 1024 * 1024:
            logger.warning("Видео слишком большое")
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
            await context.bot.delete_message(chat_id=chat.id,
                                             message_id=message.message_id)
            logger.info("Сообщение успешно удалено")
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение: {e}")

    except Exception as e:
        logger.error(f"Ошибка обработки видео: {e}")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(INSTAGRAM_REGEX),
                       handle_instagram_link))
    logger.info("🤖 Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()