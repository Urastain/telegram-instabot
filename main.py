import os
import re
import logging
import requests
import asyncio
import time
import instaloader
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, filters
import random
import certifi

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ваш_токен")

# Регулярное выражение для ссылок Instagram
INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?(\?.*)?"

def get_random_user_agent():
    """Возвращает случайный User-Agent"""
    user_agents = [
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    return random.choice(user_agents)


def extract_shortcode(url):
    """Извлекает shortcode из URL"""
    patterns = [
        r'/p/([A-Za-z0-9_-]+)', r'/reel/([A-Za-z0-9_-]+)',
        r'/tv/([A-Za-z0-9_-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# Класс для загрузки видео через Instaloader
class InstagramDownloader:

    def __init__(self):
        self.loader = instaloader.Instaloader(download_pictures=False,
                                              quiet=True)
        self.loader.context.user_agent = get_random_user_agent()
        self.loader.context._session.headers.update({
            "User-Agent": self.loader.context.user_agent,
            "X-Requested-With": "XMLHttpRequest"
        })
        self.loader.context._session.verify = certifi.where()

    def get_video_url(self, shortcode):
        for attempt in range(1, 4):
            try:
                post = instaloader.Post.from_shortcode(self.loader.context,
                                                       shortcode)
                if not post.is_video:
                    return None
                return post.video_url
            except instaloader.exceptions.ConnectionException as e:
                logger.error(f"🌐 Ошибка подключения: {e}")
                delay = random.uniform(attempt * 10, attempt * 20)
                time.sleep(delay)
        return None


# Обработчик ссылок
async def handle_instagram_link(update: Update, context):
    message = update.effective_message
    chat = update.effective_chat
    url = message.text.strip()

    if not re.search(INSTAGRAM_REGEX, url):
        return

    logger.info(f"📥 Получена ссылка: {url}")
    shortcode = extract_shortcode(url)
    if not shortcode:
        logger.error("❌ Не удалось извлечь shortcode")
        return

    temp_file = f"{shortcode}_{int(time.time())}.mp4"
    status_msg = await chat.send_message("🔄 Поиск видео...")

    try:
        downloader = InstagramDownloader()
        video_url = downloader.get_video_url(shortcode)

        if not video_url:
            # Альтернативный метод: через embed
            embed_url = f"https://www.instagram.com/p/{shortcode}/embed/"
            headers = {
                "User-Agent": get_random_user_agent(),
                "Referer": "https://www.instagram.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            response = requests.get(embed_url,
                                    headers=headers,
                                    timeout=30,
                                    verify=certifi.where())
            if response.status_code == 200:
                match = re.search(r'"video_url":"([^"]+)"', response.text)
                if match:
                    video_url = match.group(1).replace("\\u0026", "&").replace(
                        "\\/", "/")
                    logger.info("✅ Видео найдено через embed")

        if not video_url:
            await status_msg.edit_text("❌ Не удалось найти видео. Попробуйте позже.")
            return

        # Загрузка видео
        download_headers = {
            "User-Agent": get_random_user_agent(),
            "Referer": "https://www.instagram.com/",
            "Accept": "video/webm,video/ogg,video/mp4; q=0.9,*/*;q=0.8"
        }
        response = requests.get(video_url,
                                stream=True,
                                headers=download_headers,
                                timeout=30,
                                verify=certifi.where())
        response.raise_for_status()

        content_length = int(response.headers.get('Content-Length', 0))
        if content_length > 50 * 1024 * 1024:
            await status_msg.edit_text("⚠️ Видео слишком большое (лимит: 50MB)")
            return

        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Отправка видео
        with open(temp_file, "rb") as video_file:
            await chat.send_video(video=video_file,
                                  caption="📥 Видео из Instagram",
                                  supports_streaming=True)

        # Удаление сообщений
        try:
            await message.delete()
            await status_msg.delete()
            logger.info("✅ Сообщения удалены")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить сообщения: {e}")

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await status_msg.edit_text("⚠️ Не удалось загрузить видео. Попробуйте позже.")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


if __name__ == "__main__":
    bot = Bot(token=TOKEN)
    telegram_app = ApplicationBuilder().token(TOKEN).build()
    telegram_app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(INSTAGRAM_REGEX),
                       handle_instagram_link))

    logger.info("🤖 Бот запущен в режиме polling")
    telegram_app.run_polling(drop_pending_updates=True)
