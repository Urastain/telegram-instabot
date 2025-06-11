import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import requests

# Загрузка переменных из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask-приложение
app = Flask(__name__)

# Telegram bot application
application = Application.builder().token(BOT_TOKEN).build()

# Обработка команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь ссылку на видео из Instagram.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "instagram.com" not in text:
        await update.message.reply_text("Пожалуйста, пришли ссылку на Instagram.")
        return

    url = "https://instagram-downloader-download-instagram-videos-stories.p.rapidapi.com/index"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories.p.rapidapi.com"
    }
    params = {"url": text}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        video_url = response.json().get("media")
        if not video_url:
            await update.message.reply_text("Не удалось получить видео.")
            return
        await context.bot.send_video(chat_id=update.effective_chat.id, video=video_url)
    except Exception as e:
        logger.error(f"Ошибка при загрузке видео: {e}")
        await update.message.reply_text("Произошла ошибка при обработке ссылки.")

# Роут для webhook'а
@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
async def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.update_queue.put(update)
        return "ok", 200

# Установка команд
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Запуск webhook через Flask
if __name__ == "__main__":
    from telegram.ext import asyncio

    async def run():
        await application.initialize()
        await application.start()
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{WEBHOOK_SECRET}"
        await application.bot.set_webhook(url=webhook_url)
        await application.updater.start_polling()  # Только для отладки
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

    import asyncio
    asyncio.run(run())
