
import os
import requests
from flask import Flask, request

TOKEN = os.environ.get("BOT_TOKEN")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

def send_video(chat_id, video_url):
    requests.post(f"{API_URL}/sendVideo", data={
        "chat_id": chat_id,
        "video": video_url
    })

def get_instagram_video(insta_url):
    url = "https://instagram-downloader-download-instagram-videos-stories.p.rapidapi.com/index"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params={"url": insta_url})
    return response.json().get("media")

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]

        if "instagram.com" in text:
            video_url = get_instagram_video(text)
            if video_url:
                send_video(chat_id, video_url)
            else:
                requests.post(f"{API_URL}/sendMessage", data={
                    "chat_id": chat_id,
                    "text": "Не удалось получить видео. Попробуй другую ссылку."
                })
    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"
