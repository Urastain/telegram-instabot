import os
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from utils import download_instagram_video
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()

# Команда /start
async def start(update: Update, context):
    await update.message.reply_text("Отправь мне ссылку на Instagram-видео, и я загружу его для тебя.")

# Обработка ссылок
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
        logger.error(f"Ошибка при скачивании: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ Произошла ошибка при обработке ссылки.")
    finally:
        await msg.delete()

# Роут для Telegram Webhook
@app.post(WEBHOOK_PATH)
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(application.process_update(update))
    return "OK"

# Установка Webhook и запуск Flask
if __name__ == "__main__":
    async def setup():
        await application.initialize()
        await application.start()
        await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
        logger.info(f"✅ Вебхук установлен: {WEBHOOK_URL}{WEBHOOK_PATH}")
        logger.info("🤖 Telegram бот настроен и готов к работе")

    asyncio.run(setup())

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    PORT = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 Запуск Flask сервера на порту {PORT}")
    app.run(host="0.0.0.0", port=PORT)
