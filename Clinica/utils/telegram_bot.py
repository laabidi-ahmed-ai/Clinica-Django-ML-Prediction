import requests
from django.conf import settings

def send_telegram_message(chat_id, text):
    """
    Envoie un message Telegram à un utilisateur via ton bot.
    """
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }

        response = requests.post(url, json=payload)
        print("📨 Telegram Response:", response.text)

        return response.status_code == 200

    except Exception as e:
        print("❌ Telegram ERROR:", e)
        return False
