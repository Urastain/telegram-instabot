import os
import requests
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, Dispatcher, MessageHandler, filters
from telegram.ext import ContextTypes
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

def send_video(chat_id, video_url):
    requests.post(f"{API_URL}/sendVideo", data={
        "chat_id": chat_id,
        "video": video_url
    })

def get_instagram_video(insta_url):
    url = "https://instagram-downloader-download-instagram-videos-stories.p.rapidapi.com/index"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params={"url": insta_url})
    return response.json().get("media")

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
        requests.post(f"{API_URL}/sendMessage", data={
            "chat_id": chat.id,
            "text": "Не удалось получить видео. Попробуй другую ссылку."
        })

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    asyncio.run(dispatcher.process_update(update))
    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    dispatcher = application.dispatcher
    dispatcher.add_handler(MessageHandler(filters.TEXT, handle_instagram))

    # Устанавливаем webhook
    # APP_URL задаётся в Environment → BOT_URL (см. ниже)
    BOT_URL = os.environ.get("BOT_URL")  # например: https://<your-app>.onrender.com
    bot.set_webhook(f"{BOT_URL}/{TOKEN}")

    # Привязываемся к порту из Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
