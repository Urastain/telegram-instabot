import os
import instaloader
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Отправь мне ссылку на Instagram-видео.")

async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "instagram.com" not in url:
        return

    # удаляем сообщение с ссылкой
    try:
        await update.message.delete()
    except:
        pass

    await update.message.reply_text("⏳ Скачиваю видео...")

    try:
        loader = instaloader.Instaloader(dirname_pattern=tempfile.gettempdir(), save_metadata=False)
        shortcode = url.split("/")[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        video_url = post.video_url

        if video_url:
            await update.message.reply_video(video_url)
        else:
            await update.message.reply_text("⚠️ Не удалось найти видео.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при скачивании: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram))

    print("🤖 Бот запущен и слушает обновления...")
    app.run_polling()

if __name__ == "__main__":
    main()
