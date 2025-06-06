import os
import logging
import asyncio
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
    message = update.effective_message
    chat = update.effective_chat
    logger.info(f"Получено сообщение: {message.text}")
    await chat.send_message("Вы написали: " + message.text)

# --- Основной запуск бота ---
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_messages))
    logger.info("🤖 Бот запущен")
    
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await app.stop()
    except Exception as e:
        logger.error(f"Ошибка работы бота: {e}")
        await app.shutdown()

# --- Бесконечный перезапуск бота ---
def run_bot():
    loop = asyncio.get_event_loop()
    while True:
        try:
            loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Ошибка запуска: {e}")
        finally:
            loop.run_until_complete(asyncio.sleep(10))

if __name__ == "__main__":
    run_bot()
