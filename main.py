import os
import asyncio
import logging

from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import httpx

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получение переменных из окружения
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = f"https://telegram-instabot-vhl4.onrender.com/{TOKEN}"

# Flask-приложение
app = Flask(__name__)

# Создаем Telegram-приложение
application = Application.builder().token(TOKEN).build()

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь ссылку на Instagram-видео.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    if "instagram.com" in message:
        await update.message.reply_text("Обработка ссылки… (пока не реализовано)")
    else:
        await update.message.reply_text("Пожалуйста, отправь ссылку на Instagram.")

# Обработка запроса от Telegram (вебхук)
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        # Исправлено: обрабатываем update в event loop
        asyncio.run(application.process_update(update))
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "ERROR", 500

async def set_webhook():
    async with httpx.AsyncClient() as client:
        url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
        response = await client.post(url, data={"url": WEBHOOK_URL})
        if response.status_code == 200:
            logger.info(f"Вебхук установлен: {WEBHOOK_URL}")
        else:
            logger.error(f"Ошибка установки вебхука: {response.text}")

async def main():
    # Регистрируем хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Устанавливаем вебхук
    await application.initialize()
    await set_webhook()
    logger.info("Telegram приложение инициализировано")

# Запускаем все
if __name__ == "__main__":
    import threading

    # Запуск Telegram-бота в фоновом потоке
    threading.Thread(target=lambda: asyncio.run(main())).start()

    # Запуск Flask-сервера
    app.run(host="0.0.0.0", port=10000)
