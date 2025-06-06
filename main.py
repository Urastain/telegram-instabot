import os
import logging
import asyncio
import requests
import time  # ✅ Добавлен импорт time

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

# --- Функция отправки видео в Telegram ---
def send_video(chat_id: int, video_url: str) -> None:
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo", 
            data={"chat_id": chat_id, "video": video_url}
        )
        response.raise_for_status()
        logger.info(f"Видео успешно отправлено в чат {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке видео: {e}")

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

# --- Обработчик входящих сообщений ---
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.effective_message.text or ""
    chat_id = update.effective_chat.id

    if "instagram.com" not in message_text:
        return

    logger.info(f"Обработка ссылки: {message_text}")

    try:
        # Удаляем исходное сообщение
        await context.bot.delete_message(chat_id=chat_id, message_id=update.effective_message.message_id)
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    # Получаем прямую ссылку на видео
    video_url = get_instagram_video(message_text)
    if video_url:
        send_video(chat_id, video_url)
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Не удалось получить видео. Попробуйте другую ссылку.")

# --- Основной запуск бота ---
async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram))
    logger.info("🤖 Бот запущен")
    await application.run_polling()

# --- Бесконечный перезапуск бота ---
def run_bot():
    while True:
        try:
            # Создаем новый цикл событий
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Ошибка работы бота: {e}")
            logger.info("Перезапуск бота через 10 секунд...")
            time.sleep(10)  # ✅ Теперь работает без ошибок

if __name__ == "__main__":
    run_bot()
