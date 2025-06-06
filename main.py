import os
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- Переменные окружения ---
TOKEN = os.getenv("BOT_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")
if not RAPIDAPI_KEY:
    raise ValueError("RAPIDAPI_KEY is not set in environment variables")

# --- Регулярное выражение для Instagram ---
INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(\?.*)?"

# --- Загрузка видео через RapidAPI ---
def get_instagram_video(insta_url: str) -> str | None:
    api_endpoint = "https://instagram-downloader-download-instagram-videos-stories.p.rapidapi.com/index" 
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories.p.rapidapi.com"
    }

    try:
        response = requests.get(api_endpoint, headers=headers, params={"url": insta_url})
        response.raise_for_status()
        data = response.json()
        return data.get("media")
    except Exception as e:
        logger.error(f"Ошибка получения видео: {e}")
        return None

# --- Обработчик сообщений ---
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    if not re.search(INSTAGRAM_REGEX, message.text):
        return

    logger.info(f"Обнаружена ссылка: {message.text}")

    try:
        await context.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    video_url = get_instagram_video(message.text)
    if video_url:
        try:
            await context.bot.send_video(chat_id=chat.id, video=video_url, supports_streaming=True)
        except Exception as e:
            logger.error(f"Ошибка отправки видео: {e}")
    else:
        await context.bot.send_message(chat_id=chat.id, text="❌ Не удалось получить видео. Попробуйте другую ссылку.")

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
