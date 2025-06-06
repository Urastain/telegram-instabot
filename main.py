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
BOT_TOKEN = os.getenv("BOT_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")
if not RAPIDAPI_KEY:
    raise ValueError("RAPIDAPI_KEY is not set in environment variables")

# --- Получение прямой ссылки на видео через RapidAPI ---
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
        logger.error(f"Не удалось получить видео: {e}")
        return None

# --- Обработчик сообщений ---
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.effective_message.text or ""
    chat_id = update.effective_chat.id

    if "instagram.com" not in message_text:
        return

    logger.info(f"Обнаружена ссылка: {message_text}")

    try:
        # Удаляем исходное сообщение
        await context.bot.delete_message(chat_id=chat_id, message_id=update.effective_message.message_id)
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    # Получаем прямую ссылку на видео
    video_url = get_instagram_video(message_text)
    if video_url:
        try:
            # Отправляем видео
            await context.bot.send_video(chat_id=chat_id, video=video_url, supports_streaming=True)
        except Exception as e:
            logger.error(f"Ошибка при отправке видео: {e}")
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Не удалось скачать видео. Попробуйте другую ссылку.")

# --- Основной запуск бота ---
async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram))
    logger.info("🤖 Бот запущен")
    await application.run_polling()

# --- Бесконечный перезапуск бота ---
def run_bot():
    loop = asyncio.get_event_loop()
    while True:
        try:
            loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Ошибка работы бота: {e}")
            logger.info("Перезапуск бота через 10 секунд...")
            loop.run_until_complete(asyncio.sleep(10))

if __name__ == "__main__":
    run_bot()
