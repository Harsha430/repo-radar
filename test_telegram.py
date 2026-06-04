import os
from dotenv import load_dotenv
import requests

# Load from .env
load_dotenv()

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print(f"Loaded Token: {bot_token}")
print(f"Loaded Chat ID: {chat_id}")

url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": "🚀 Hello! The Telegram Bot is officially working!"
}

print(f"Sending request to Telegram API...")
response = requests.post(url, json=payload)

print(f"Response Status: {response.status_code}")
print(f"Response Body: {response.text}")
