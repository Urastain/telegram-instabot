import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode
from utils import download_instagram_video
from dotenv import load_dotenv
import asyncio

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=TOKEN)
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(application.process_update(update))
    return "OK"

@app.route("/")
def index():
    return "✅ Bot is running"

# /start
async def start(update: Update, context):
    await update.message.reply_text("Отправь ссылку на Instagram-видео, и я загружу его для тебя.")

# обработка сообщений
async def handle_message(update: Update, context):
    url = update.message.text
    chat_id = update.effective_chat.id
    msg = await context.bot.send_message(chat_id=chat_id, text="🔄 Загружаю видео...")

    try:
        video_url = download_instagram_video(url)
        if video_url:
            await context.bot.send_video(chat_id=chat_id, video=video_url)
        else:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Не удалось получить видео.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ Ошибка при загрузке.")
    finally:
        await msg.delete()

if __name__ == "__main__":
    async def setup():
        await application.initialize()
        await application.start()
        await bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("🤖 Webhook установлен и приложение запущено")

    asyncio.run(setup())
    app.run(host="0.0.0.0", port=PORT)
