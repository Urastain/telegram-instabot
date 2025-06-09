import os
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Переменные окружения ---
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

# --- Регулярное выражение для Instagram ---
INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(\?.*)?"

# --- Загрузка видео из Instagram ---
async def download_instagram_video(shortcode: str) -> str | None:
    try:
        import instaloader
        L = instaloader.Instaloader(download_pictures=False, quiet=True)
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        if not post.is_video:
            return None
            
        video_url = post.video_url
        response = requests.get(video_url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Проверка размера файла (ограничение Telegram — 50MB)
        content_length = int(response.headers.get('Content-Length', 0))
        if content_length > 50 * 1024 * 1024:
            logger.warning("Видео слишком большое")
            return None

        temp_file = f"{shortcode}.mp4"
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return temp_file
    except Exception as e:
        logger.error(f"Ошибка загрузки Instagram-видео: {e}")
        return None

# --- Обработчик сообщений ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    
    if not re.search(INSTAGRAM_REGEX, message.text):
        return

    logger.info(f"Получена ссылка: {message.text}")
    
    # Удаляем исходное сообщение
    try:
        await chat.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    # Извлекаем короткий код поста
    shortcode = message.text.split("/")[-2]
    
    # Скачиваем и отправляем видео
    temp_file = await asyncio.get_event_loop().run_in_executor(None, download_instagram_video, shortcode)
    
    if temp_file and os.path.exists(temp_file):
        try:
            with open(temp_file, 'rb') as video_file:
                await chat.send_video(video=video_file, supports_streaming=True)
        finally:
            os.remove(temp_file)

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
            loop = asyncio.new_event_loop()
            loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Ошибка работы бота: {e}")
            logger.info("Перезапуск через 10 секунд...")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
