import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Переменные окружения ---
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

# --- Обработчик сообщений ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    logger.info(f"Получено сообщение: {message.text}")
    await message.reply_text("Привет! Пришли ссылку на Instagram-видео.")

# --- Основной запуск бота ---
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    logger.info("🤖 Бот запущен")
    await app.run_polling()

# --- Бесконечный перезапуск бота ---
def run_bot():
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            logger.error(f"Ошибка работы бота: {e}")
            logger.info("Перезапуск через 10 секунд...")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
