import os
import asyncio
import re
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright

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

# Глобальные переменные
application = None

# Инициализация приложения
def init_telegram_app():
    global application
    
    # Создаем приложение Telegram
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    
    # Обработчик Instagram ссылок
    instagram_filter = filters.TEXT & filters.Regex(
        r"https?://(www\.)?instagram\.com/(p|reel|stories)/"
    )
    application.add_handler(MessageHandler(instagram_filter, handle_instagram_link))
    
    # Инициализируем приложение
    application.initialize()
    logger.info("Приложение Telegram инициализировано")

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли ссылку на Instagram-видео.")

# Класс для скачивания видео
class InstagramDownloader:
    async def get_video_url(self, url: str) -> str | None:
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1",
                    viewport={"width": 390, "height": 844}
                )
                page = await context.new_page()
                
                # Настройки для обхода блокировок
                await page.set_extra_http_headers({
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.instagram.com/',
                })
                
                logger.info(f"Загружаю страницу: {url}")
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(3)  # Задержка для загрузки контента
                
                # Пробуем найти видео
                video_element = await page.query_selector('video')
                if not video_element:
                    video_element = await page.query_selector('source[type="video/mp4"]')
                
                if video_element:
                    video_url = await video_element.get_attribute('src')
                    logger.info(f"Найдено видео: {video_url}")
                    return video_url
                
                logger.error("Видео не найдено")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка Playwright: {str(e)}")
            return None
        finally:
            if browser:
                await browser.close()

# Обработчик Instagram ссылок
async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # Проверка формата ссылки
    if not re.match(r"^https?://(?:www\.)?instagram\.com/(?:p|reel|stories)/[a-zA-Z0-9_-]+", url):
        await update.message.reply_text("❌ Пожалуйста, отправьте прямую ссылку на пост/рил/сторис Instagram.")
        return

    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

    status_msg = await update.message.reply_text("🔄 Обрабатываю ссылку...")

    downloader = InstagramDownloader()
    video_url = await downloader.get_video_url(url)

    if not video_url:
        await status_msg.edit_text("❌ Не удалось получить видео. Возможные причины:\n- Приватный аккаунт\n- Ограничения Instagram\n- Техническая ошибка")
        return

    await status_msg.edit_text("✅ Видео найдено! Скачиваю...")

    try:
        # Скачиваем видео
        response = requests.get(video_url, headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1',
            'Referer': 'https://www.instagram.com/'
        }, stream=True, timeout=30)
        
        response.raise_for_status()
        
        # Отправляем видео пользователю
        await update.message.reply_video(
            video=response.raw,
            caption="✅ Видео из Instagram",
            supports_streaming=True
        )
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Ошибка при отправке видео: {str(e)}")
        await status_msg.edit_text("❌ Ошибка при загрузке видео")

# Установка вебхука
async def setup_webhook():
    webhook_url = f"{BOT_URL}/{TOKEN}"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Вебхук установлен: {webhook_url}")

# Инициализация при запуске
init_telegram_app()

# Flask приложение (только для вебхука)
from flask import Flask, request
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.update_queue.put(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Ошибка обработки обновления: {e}")
        return "ERROR", 500

# Запуск сервера
if __name__ == "__main__":
    # Установка вебхука
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_webhook())
    
    # Запуск Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
else:
    # Для production среды (Render.com)
    @app.before_first_request
    async def on_startup():
        await setup_webhook()
