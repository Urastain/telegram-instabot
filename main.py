import os
import re
import asyncio
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright
from flask import Flask, request

# Логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = os.getenv("BOT_URL")

if not TOKEN or not BOT_URL:
    logger.error("❌ Не заданы BOT_TOKEN или BOT_URL")
    exit(1)

# Flask-приложение
app = Flask(__name__)
application = None  # Telegram Application

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Пришли мне ссылку на Instagram-видео (reel, пост или stories).")

# Класс загрузки Instagram-видео
class InstagramDownloader:
    async def get_video_url(self, url: str) -> str | None:
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=[
                    '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'
                ])
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1",
                    viewport={"width": 390, "height": 844}
                )
                page = await context.new_page()
                await page.set_extra_http_headers({
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.instagram.com/',
                })

                logger.info(f"Загружаю: {url}")
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(3)

                video_element = await page.query_selector('video') or await page.query_selector('source[type="video/mp4"]')
                if video_element:
                    return await video_element.get_attribute('src')
                return None
        except Exception as e:
            logger.error(f"Ошибка Playwright: {e}")
            return None
        finally:
            if browser:
                await browser.close()

# Обработка ссылок Instagram
async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not re.match(r"^https?://(?:www\.)?instagram\.com/(?:p|reel|stories)/[a-zA-Z0-9_-]+", url):
        await update.message.reply_text("❌ Неверная ссылка. Пример: https://www.instagram.com/reel/...")
        return

    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    status_msg = await update.message.reply_text("⏳ Обрабатываю ссылку...")

    downloader = InstagramDownloader()
    video_url = await downloader.get_video_url(url)

    if not video_url:
        await status_msg.edit_text("❌ Не удалось найти видео. Возможно, аккаунт приватный.")
        return

    await status_msg.edit_text("📥 Скачиваю видео...")

    try:
        response = requests.get(video_url, headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)',
            'Referer': 'https://www.instagram.com/'
        }, stream=True, timeout=30)
        response.raise_for_status()

        await update.message.reply_video(
            video=response.raw,
            caption="✅ Вот ваше видео!",
            supports_streaming=True
        )
        await status_msg.delete()

    except Exception as e:
        logger.error(f"Ошибка отправки видео: {e}")
        await status_msg.edit_text("❌ Ошибка при отправке видео.")

# Вебхук
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.update_queue.put(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "ERROR", 500

# Установка вебхука
async def setup_webhook():
    webhook_url = f"{BOT_URL}/{TOKEN}"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"✅ Вебхук установлен: {webhook_url}")

# Главная асинхронная функция
async def main():
    global application

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    instagram_filter = filters.TEXT & filters.Regex(r"https?://(www\.)?instagram\.com/(p|reel|stories)/")
    application.add_handler(MessageHandler(instagram_filter, handle_instagram_link))

    await application.initialize()
    await setup_webhook()
    logger.info("✅ Telegram приложение инициализировано")

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
