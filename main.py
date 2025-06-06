import os
import requests
import logging
import asyncio

from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
TOKEN = os.environ.get("BOT_TOKEN")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
BOT_URL = os.environ.get("BOT_URL")  # Например: https://your-app-name.pythonanywhere.com

API_URL = f"https://api.telegram.org/bot{TOKEN}"
bot = Bot(token=TOKEN)
app = Flask(__name__)

# Создание Telegram приложения
application = Application.builder().token(TOKEN).build()

# Получение видео из Instagram через RapidAPI
def get_instagram_video(insta_url):
    url = "https://instagram-downloader-download-instagram-videos-stories.p.rapidapi.com/index"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params={"url": insta_url})
    return response.json().get("media")

# Отправка видео
def send_video(chat_id, video_url):
    requests.post(f"{API_URL}/sendVideo", data={
        "chat_id": chat_id,
        "video": video_url
    })

# Обработчик входящих сообщений
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    text = message.text or ""
    if "instagram.com" not in text:
        return

    video_url = get_instagram_video(text)
    if video_url:
        send_video(chat.id, video_url)
    else:
        await context.bot.send_message(
            chat_id=chat.id,
            text="Не удалось получить видео. Попробуй другую ссылку."
        )

# Обработка webhook Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    asyncio.run(application.process_update(update))
    return "OK"

# Простой GET-запрос для проверки работоспособности
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

# Главная точка входа
if __name__ == "__main__":
    # Регистрируем обработчик
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram))

    async def main():
        # Устанавливаем webhook
        await bot.set_webhook(f"{BOT_URL}/{TOKEN}")
        logger.info(f"Webhook установлен на {BOT_URL}/{TOKEN}")

        # Запуск Flask
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)

    asyncio.run(main())
