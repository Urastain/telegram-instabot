import os
import logging
import asyncio
import time  # ✅ Добавлен импорт
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- Логирование ---
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Переменные окружения ---
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

# --- Обработчик сообщений ---
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Получено сообщение: {update.effective_message.text}")
    # Ваш код обработки ссылок из Instagram

# --- Основной запуск бота ---
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_messages))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("🤖 Бот запущен")
    await app.idle()

# --- Бесконечный перезапуск ---
def run_bot():
    while True:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Ошибка работы бота: {str(e)}")
            logger.info("Перезапуск бота через 10 секунд...")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
