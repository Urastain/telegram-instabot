import os
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = os.getenv("BOT_URL")

# Flask-приложение
app = Flask(__name__)
bot = Bot(token=TOKEN)

# Telegram Application (аналог Dispatcher)
application = Application.builder().token(TOKEN).build()

# Обработчик команды /start
async def start(update: Update, context):
    await update.message.reply_text("Привет! Пришли ссылку на Instagram-видео.")

# Обработка входящих обновлений
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

# Устанавливаем webhook
async def set_webhook():
    url = f"{BOT_URL}/{TOKEN}"
    await bot.set_webhook(url)

# Запуск сервера
if __name__ == "__main__":
    # Регистрируем handlers
    application.add_handler(CommandHandler("start", start))

    # Установка webhook
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())

    # Запускаем Flask
    app.run(host="0.0.0.0", port=10000)
