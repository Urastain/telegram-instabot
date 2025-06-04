import os
import requests
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import instaloader
import asyncio
import logging

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Создаём приложение Telegram
application = Application.builder().token(TOKEN).build()

# Функция отправки видео
def send_video(chat_id, video_url):
    requests.post(f"{API_URL}/sendVideo", data={
        "chat_id": chat_id,
        "video": video_url
    })

# Получение видео из Instagram через RapidAPI
def get_instagram_video(insta_url):
    url = "https://instagram-downloader-download-instagram-videos-stories.p.rapidapi.com/index"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params={"url": insta_url})
    return response.json().get("media")

# Обработчик сообщений
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

# Webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    asyncio.run(application.process_update(update))
    return "OK"

# Тестовый GET-эндпоинт
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

if __name__ == "__main__":
    # Регистрируем обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram))

    # Устанавливаем webhook
    import asyncio

bot = Bot(token=TOKEN)
asyncio.run(bot.set_webhook(f"{BOT_URL}/{TOKEN}"))


    # Flask-сервер
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
