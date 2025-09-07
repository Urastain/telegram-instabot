import time
import requests

while True:
    try:
        requests.get(f"https://api.telegram.org/bot <TOKEN>/getMe".replace(
            "<TOKEN>", os.getenv("TELEGRAM_BOT_TOKEN", "токен")),
                     timeout=10,
                     verify=certifi.where())
        print("🔄 Пинг к Telegram: OK")
    except Exception as e:
        print(f"❌ Ошибка пинга: {e}")
    time.sleep(60)
