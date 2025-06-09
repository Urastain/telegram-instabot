import os
import logging
import asyncio
import requests
from flask import Flask, request

from telegram import Update, Bot
from telegram.ext import (
    Application, MessageHandler, filters, ContextTypes
)

# ---------------------- Конфигурация и логирование ----------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Получение переменных окружения
TOKEN = os.environ.get("BOT_TOKEN")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
BOT_URL = os.environ.get("BOT_URL")

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")
if not RAPIDAPI_KEY:
    raise ValueError("RAPIDAPI_KEY is not set in environment variables")
if not BOT_URL:
    raise ValueError("BOT_URL is not set in environment variables")

API_URL = f"https://api.telegram.org/bot{TOKEN}"

# ---------------------- Инициализация ----------------------

bot = Bot(token=TOKEN)
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# ---------------------- Функции ----------------------

def send_video(chat_id: int, video_url: str):
    """Отправка видео пользователю."""
    try:
        response = requests.post(
            f"{API_URL}/sendVideo",
            data={"chat_id": chat_id, "video": video_url}
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Ошибка при отправке видео: {e}")

def get_instagram_video(insta_url: str) -> str | None:
    """Получение прямой ссылки на видео с Instagram через RapidAPI."""
    api_url = "https://instagram-downloader-download-instagram-videos-stories.p.rapidapi.com/index"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories.p.rapidapi.com"
    }
    try:
        response = requests.get(api_url, headers=headers, params={"url": insta_url})
        response.raise_for_status()
        data = response.json()
        return data.get("media")
    except Exception as e:
        logger.error(f"Ошибка при получении видео с Instagram: {e}")
        return None

# ---------------------- Обработчик сообщений ----------------------

async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений от пользователей."""
    message = update.effective_message
    chat = update.effective_chat
    text = message.text or ""

    if "instagram.com" not in text:
        return

    await context.bot.delete_message(chat.id, message.message_id)

    video_url = get_instagram_video(text)
    if video_url:
        send_video(chat.id, video_url)
    else:
        await context.bot.send_message(
            chat_id=chat.id,
            text="❌ Не удалось получить видео. Попробуй другую ссылку."
        )

# ---------------------- Flask: webhook endpoints ----------------------

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """Обработка входящих обновлений через Webhook."""
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    asyncio.run(application.process_update(update))
    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "✅ Bot is running!"

# ---------------------- Запуск ----------------------

if __name__ == "__main__":
    # Регистрируем обработчик
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram)
    )

    # Устанавливаем Webhook
    asyncio.run(bot.set_webhook(f"{BOT_URL}/{TOKEN}"))
    logger.info(f"Webhook установлен: {BOT_URL}/{TOKEN}")

    # Запускаем Flask-сервер
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
