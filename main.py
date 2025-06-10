import os
import asyncio
import logging
import tempfile
import threading
import time
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import httpx
import yt_dlp
from urllib.parse import urlparse

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получение переменных из окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

WEBHOOK_URL = f"https://telegram-instabot-vhl4.onrender.com/{TOKEN}"
PORT = int(os.getenv("PORT", 10000))

# Flask-приложение
app = Flask(__name__)

# Глобальная переменная для приложения
telegram_app = None

class InstagramDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
    
    def download_video(self, url):
        """Скачивает видео с Instagram и возвращает путь к файлу"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                self.ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
                
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    # Получаем информацию о видео
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'instagram_video')
                    
                    # Скачиваем видео
                    ydl.download([url])
                    
                    # Находим скачанный файл
                    for file in os.listdir(temp_dir):
                        if file.endswith(('.mp4', '.mkv', '.webm')):
                            file_path = os.path.join(temp_dir, file)
                            # Читаем файл в память
                            with open(file_path, 'rb') as f:
                                return f.read(), title
            
            return None, None
        except Exception as e:
            logger.error(f"Ошибка при скачивании видео: {e}")
            return None, None

downloader = InstagramDownloader()

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🎬 Привет! Я бот для скачивания видео с Instagram.\n\n"
        "📋 Как использовать:\n"
        "• Отправь мне ссылку на Instagram пост/reel\n"
        "• Жди, пока я скачаю видео\n"
        "• Получи файл!\n\n"
        "⚠️ Поддерживаются только публичные посты"
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()
    
    # Проверяем, является ли сообщение ссылкой Instagram
    if not any(domain in message.lower() for domain in ["instagram.com", "instagr.am"]):
        await update.message.reply_text(
            "❌ Пожалуйста, отправь корректную ссылку на Instagram пост или reel."
        )
        return
    
    # Отправляем сообщение о начале обработки
    processing_msg = await update.message.reply_text("⏳ Обрабатываю ссылку...")
    
    try:
        # Скачиваем видео
        video_data, title = downloader.download_video(message)
        
        if video_data and title:
            # Удаляем сообщение об обработке
            await processing_msg.delete()
            
            # Проверяем размер файла (Telegram лимит 50MB)
            if len(video_data) > 50 * 1024 * 1024:
                await update.message.reply_text("❌ Файл слишком большой (>50MB)")
                return
            
            # Отправляем видео
            await update.message.reply_video(
                video=video_data,
                caption=f"📹 {title[:100]}..." if len(title) > 100 else f"📹 {title}",
                filename=f"{title[:50]}.mp4"
            )
            
            # Удаляем исходное сообщение со ссылкой
            try:
                await update.message.delete()
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение: {e}")
                
        else:
            await processing_msg.edit_text(
                "❌ Не удалось скачать видео. Возможные причины:\n"
                "• Пост приватный\n"
                "• Неверная ссылка\n"
                "• Временная недоступность Instagram"
            )
            
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await processing_msg.edit_text("❌ Произошла ошибка при скачивании видео.")

# Flask маршруты
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "alive",
        "timestamp": time.time(),
        "bot_status": "active" if telegram_app else "inactive"
    })

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, telegram_app.bot)
        
        # Создаем задачу для обработки обновления
        asyncio.create_task(telegram_app.process_update(update))
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "ERROR", 500

# Keep-alive функционал
def keep_alive():
    """Функция для поддержания активности на Render"""
    while True:
        try:
            time.sleep(25 * 60)  # 25 минут
            # Делаем запрос к самому себе
            with httpx.Client(timeout=30) as client:
                response = client.get(f"https://telegram-instabot-vhl4.onrender.com/")
                logger.info(f"Keep-alive ping: {response.status_code}")
        except Exception as e:
            logger.error(f"Keep-alive error: {e}")

async def setup_telegram():
    """Настройка Telegram бота"""
    global telegram_app
    
    # Создаем приложение
    telegram_app = Application.builder().token(TOKEN).build()
    
    # Регистрируем хендлеры
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Инициализируем приложение
    await telegram_app.initialize()
    
    # Устанавливаем вебхук
    async with httpx.AsyncClient(timeout=30) as client:
        webhook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
        response = await client.post(webhook_url, data={"url": WEBHOOK_URL})
        
        if response.status_code == 200:
            logger.info(f"✅ Вебхук установлен: {WEBHOOK_URL}")
        else:
            logger.error(f"❌ Ошибка установки вебхука: {response.text}")
            raise Exception("Не удалось установить вебхук")
    
    logger.info("🤖 Telegram бот настроен и готов к работе")

def run_telegram_setup():
    """Запуск настройки Telegram в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_telegram())

if __name__ == "__main__":
    try:
        # Запуск настройки Telegram в отдельном потоке
        telegram_thread = threading.Thread(target=run_telegram_setup, daemon=True)
        telegram_thread.start()
        
        # Даем время на инициализацию
        time.sleep(5)
        
        # Запуск keep-alive в отдельном потоке
        keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        keep_alive_thread.start()
        
        logger.info(f"🚀 Запуск Flask сервера на порту {PORT}")
        
        # Запуск Flask сервера
        app.run(
            host="0.0.0.0", 
            port=PORT, 
            debug=False,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise
