import os
import asyncio
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters, Application

TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = os.getenv("BOT_URL")

bot = Bot(token=TOKEN)
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(bot_application.process_update(update))
    return "OK", 200

async def start(update, context):
    await update.message.reply_text("Привет! Пришли ссылку на Instagram-видео.")

# Создаём Telegram-приложение (dispatcher)
bot_application = Application.builder().token(TOKEN).build()
bot_application.add_handler(CommandHandler("start", start))

# Установка webhook при запуске
async def set_webhook():
    webhook_url = f"{BOT_URL}/{TOKEN}"
    await bot.set_webhook(url=webhook_url)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    app.run(host="0.0.0.0", port=10000)
