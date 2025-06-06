import os
import logging
import asyncio
import time  # ✅ Убедитесь, что импортирован
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- Переменные окружения ---
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

# --- Обработчик сообщений ---
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Получено сообщение: {update.effective_message.text}")
    await update.effective_chat.send_message("Вы написали: " + update.effective_message.text)

# --- Основной запуск бота ---
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_messages))
    logger.info("🤖 Бот запущен")
    await app.run_polling()  # ✅ Используем корректный метод

# --- Бесконечный перезапуск бота ---
def run_bot():
    while True:
        try:
            # Используем asyncio.run() вместо вручную созданного цикла
            asyncio.run(main())
        except Exception as e:
            logger.error(f"Ошибка работы бота: {e}")
            logger.info("Перезапуск бота через 10 секунд...")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
