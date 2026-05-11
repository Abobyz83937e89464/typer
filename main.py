import os
import requests
import logging
import asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- ТВОИ ДАННЫЕ (ВШИТЫ) ---
API_ID = 28696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
PHONE = '+15185316181'

# Firebase данные
DB_SECRET = "03FjyGvc0J1Vr7qcLei0tc0IXNRKEsuZg2Icc3fd"
DB_URL = "https://typing-939e2-default-rtdb.firebaseio.com/messages.json"
# ---------------------------

app = Flask(__name__)

async def telegram_worker():
    # Файл сессии сохранится как 'session_v1.session'
    client = TelegramClient('session_v1', API_ID, API_HASH)

    @client.on(events.NewMessage)
    async def handler(event):
        # Собираем данные сообщения
        payload = {
            "text": event.raw_text,
            "sender_id": event.sender_id,
            "chat_id": event.chat_id,
            "date": str(event.date)
        }
        
        # Отправка в Firebase через Database Secret
        try:
            url_with_auth = f"{DB_URL}?auth={DB_SECRET}"
            response = requests.post(url_with_auth, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Firebase засейвил: {event.raw_text[:20]}...")
            else:
                logger.error(f"❌ Ошибка Firebase: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"❌ Ошибка сети при отправке: {e}")

    logger.info("🎬 Подключаемся к Telegram...")
    
    # Запуск с вводом номера телефона
    await client.start(phone=PHONE)
    
    logger.info("✅ Бот авторизован и слушает сообщения!")
    await client.run_until_disconnected()

@app.route('/')
def health():
    return "Status: Online. Auth: Database Secret.", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Flask в фоне
    Thread(target=run_flask, daemon=True).start()

    # Telethon в основном потоке
    try:
        asyncio.run(telegram_worker())
    except KeyboardInterrupt:
        logger.info("Бот выключен.")
