import os
import logging
import asyncio
import time  # ✅ Добавлен импорт
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Переменные окружения ---
TOKEN = os.getenv("BOT_TOKEN")
INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(\?.*)?"

# --- Обработчик сообщений ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    
    if not re.search(INSTAGRAM_REGEX, message.text):
        return
    
    logger.info(f"Обнаружена ссылка: {message.text}")
    
    try:
        # Удаляем исходное сообщение
        await chat.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    # Здесь добавьте логику загрузки и отправки видео (см. ниже)

# --- Основной запуск бота ---
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Regex(INSTAGRAM_REGEX), handle_message))
    logger.info("🤖 Бот запущен")
    await app.run_polling()

# --- Бесконечный перезапуск бота ---
def run_bot():
    while True:
        try:
            # Создаем новый цикл событий
            loop = asyncio.new_event_loop()
            loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Ошибка работы бота: {e}")
            logger.info("Перезапуск через 10 секунд...")
            time.sleep(10)  # ✅ Используем time.sleep(), т.к. asyncio.sleep() может не работать в некоторых случаях

if __name__ == "__main__":
    run_bot()
