import os
import re
import logging
import requests
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
APP_URL = os.getenv("APP_URL")  # Пример: https://your-project.onrender.com 
PORT = int(os.getenv("PORT", "10000"))

# Бот
bot = Bot(token=TOKEN)

# Flask
app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    await application.update_queue.put(update)
    return "ok"

@app.route("/")
def index():
    return "Telegram бот работает!"

# Обработка ссылок
INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(\?.*)?"

async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    if not re.search(INSTAGRAM_REGEX, message.text):
        return

    shortcode = message.text.split("/")[-2]
    temp_file = f"{shortcode}.mp4"

    try:
        import instaloader
        L = instaloader.Instaloader(download_pictures=False, quiet=True)
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        if not post.is_video:
            await message.reply_text("⚠️ Это не видео.")
            return

        video_url = post.video_url
        response = requests.get(video_url, stream=True, timeout=30)
        response.raise_for_status()

        size = int(response.headers.get("Content-Length", 0))
        if size > 50 * 1024 * 1024:
            await message.reply_text("❌ Видео слишком большое (>50MB).")
            return

        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(8192):
                if chunk:
                    f.write(chunk)

        with open(temp_file, "rb") as video:
            await context.bot.send_video(chat_id=chat.id, video=video, supports_streaming=True)

        await context.bot.delete_message(chat_id=chat.id, message_id=message.message_id)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.reply_text("❌ Ошибка обработки видео.")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Инициализация
application = Application.builder().token(TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(INSTAGRAM_REGEX), handle_instagram))

application.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=f"{APP_URL}/webhook/{TOKEN}"
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)