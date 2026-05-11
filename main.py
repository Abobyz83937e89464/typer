import os
import requests
import logging
import asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events

# Логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- ТВОИ ДАННЫЕ ---
API_ID = 28696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
SESSION_NAME = 'session_name' # Должен лежать файл session_name.session

DB_SECRET = "03FjyGvc0J1Vr7qcLei0tc0IXNRKEsuZg2Icc3fd"
DB_URL = "https://typing-939e2-default-rtdb.firebaseio.com/messages.json"
# -------------------

app = Flask(__name__)

async def telegram_worker():
    # Создаем клиент, указывая имя сессии
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    @client.on(events.NewMessage)
    async def handler(event):
        payload = {
            "text": event.raw_text,
            "sender_id": event.sender_id,
            "chat_id": event.chat_id,
            "date": str(event.date)
        }
        try:
            url_with_auth = f"{DB_URL}?auth={DB_SECRET}"
            requests.post(url_with_auth, json=payload, timeout=10)
            logger.info(f"✅ Данные в Firebase!")
        except Exception as e:
            logger.error(f"❌ Ошибка базы: {e}")

    logger.info(f"🎬 Попытка входа по сессии: {SESSION_NAME}...")
    
    await client.connect()
    
    # Проверка, подцепилась ли сессия
    if not await client.is_user_authorized():
        logger.error("❌ ОШИБКА: Сессия не авторизована! Проверь наличие .session файла.")
        return

    logger.info("✅ Успешный вход! Бот мониторит сообщения.")
    await client.run_until_disconnected()

@app.route('/')
def health():
    return "Status: Active", 200

if __name__ == '__main__':
    # Flask для Render (чтобы не засыпал)
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    try:
        asyncio.run(telegram_worker())
    except Exception as e:
        logger.error(f"FATAL: {e}")
