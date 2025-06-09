import os
import asyncio
import re
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright
from flask import Flask, request

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = os.getenv("BOT_URL")

# Проверка переменных окружения
if not TOKEN or not BOT_URL:
    logger.error("ОШИБКА: Не заданы BOT_TOKEN или BOT_URL в переменных окружения")
    exit(1)

# Глобальная переменная приложения Telegram
application = None

# Инициализация Telegram
def init_telegram_app():
    global application

    application = Application.builder().token(TOKEN).build()

    # Команда /start
    application.add_handler(CommandHandler("start", start))

    # Обработка Instagram-ссылок
    instagram_filter = filters.TEXT & filters.Regex(
        r"https?://(www\.)?instagram\.com/(p|reel|stories)/"
    )
    application.add_handler(MessageHandler(instagram_filter, handle_instagram_link))

    application.initialize()
    logger.info("Telegram приложение инициализировано")

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли ссылку на Instagram-видео.")

# Класс скачивания видео
class InstagramDownloader:
    async def get_video_url(self, url: str) -> str | None:
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox']
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1",
                    viewport={"width": 390, "height": 844}
                )
                page = await context.new_page()
                await page.set_extra_http_headers({
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.instagram.com/',
                })
                logger.info(f"Загружаю страницу: {url}")
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(3)

                video_element = await page.query_selector('video')
                if not video_element:
                    video_element = await page.query_selector('source[type="video/mp4"]')

                if video_element:
                    return await video_element.get_attribute('src')
                return None
        except Exception as e:
            logger.error(f"Ошибка Playwright: {e}")
            return None
        finally:
            if browser:
                await browser.close()

# Обработка Instagram-ссылки
async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not re.match(r"^https?://(?:www\.)?instagram\.com/(?:p|reel|stories)/[a-zA-Z0-9_-]+", url):
        await update.message.reply_text("❌ Нужна ссылка на пост/рил/сторис Instagram.")
        return

    try:
        await update.message.delete()
    except:
        pass

    status_msg = await update.message.reply_text("🔄 Обрабатываю ссылку...")

    downloader = InstagramDownloader()
    video_url = await downloader.get_video_url(url)

    if not video_url:
        await status_msg.edit_text("❌ Не удалось получить видео. Возможно, профиль приватный или ошибка загрузки.")
        return

    await status_msg.edit_text("✅ Видео найдено! Отправляю...")

    try:
        response = requests.get(video_url, stream=True, timeout=30)
        response.raise_for_status()

        await update.message.reply_video(
            video=response.raw,
            caption="✅ Видео из Instagram",
            supports_streaming=True
        )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Ошибка при отправке видео: {e}")
        await status_msg.edit_text("❌ Ошибка при загрузке видео")

# Установка вебхука
async def setup_webhook():
    webhook_url = f"{BOT_URL}/{TOKEN}"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Вебхук установлен: {webhook_url}")

# Инициализация
init_telegram_app()

# Flask
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put_nowait(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Ошибка обработки обновления: {e}")
        return "ERROR", 500

# Запуск сервера
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_webhook())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
