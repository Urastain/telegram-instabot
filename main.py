import os
import logging
import asyncio
import requests

from flask import Flask, request
from telegram import Update, Bot
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
BOT_URL = os.getenv("BOT_URL")

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")
if not RAPIDAPI_KEY:
    raise ValueError("RAPIDAPI_KEY is not set in environment variables")
if not BOT_URL:
    raise ValueError("BOT_URL is not set in environment variables")

# --- Инициализация объектов ---
bot = Bot(token=TOKEN)
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()


# --- Функция отправки видео в Telegram ---
def send_video(chat_id: int, video_url: str) -> None:
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendVideo",
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

    video_url = get_instagram_video(message_text)
    if video_url:
        send_video(chat_id, video_url)
        await context.bot.delete_message(chat_id=chat_id, message_id=update.effective_message.message_id)
    else:
        await context.bot.send_message(chat_id=chat_id, text="Не удалось получить видео. Попробуй другую ссылку.")


# --- Webhook для Telegram ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, bot)
    asyncio.run(application.process_update(update))
    return "OK", 200


# --- Проверка статуса приложения ---
@app.route("/", methods=["GET"])
def index():
    return "Instagram Downloader Bot is running!", 200


# --- Точка входа ---
if __name__ == "__main__":
    # Регистрация обработчиков
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram))

    # Установка Webhook
    logger.info("Установка Webhook...")
    asyncio.run(bot.set_webhook(f"{BOT_URL}/{TOKEN}"))

    # Запуск Flask-сервера
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Сервер запущен на порту {port}")
    app.run(host="0.0.0.0", port=port)
