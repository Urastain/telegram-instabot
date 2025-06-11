import os
import requests

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

def download_instagram_video(insta_url):
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories.p.rapidapi.com"
    }
    params = {"url": insta_url}
    response = requests.get("https://instagram-downloader-download-instagram-videos-stories.p.rapidapi.com/index", headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("media")
    return None
