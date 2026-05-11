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
SESSION_NAME = 'Session_name' 

DB_SECRET = "03FjyGvc0J1Vr7qcLei0tc0IXNRKEsuZg2Icc3fd"
DB_BASE_URL = "https://typing-939e2-default-rtdb.firebaseio.com"
# -------------------

app = Flask(__name__)

async def telegram_worker():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    @client.on(events.NewMessage)
    async def handler(event):
        # Определяем имя чата для твоей админки
        chat_name = "Чат"
        if event.is_private:
            user = await event.get_sender()
            chat_name = f"👤 {user.first_name or 'User'}"
        else:
            chat = await event.get_chat()
            chat_name = f"👥 {getattr(chat, 'title', 'Group')}"

        # Формируем данные для узла chats/list (как хочет твоя админка)
        chat_info = {"name": chat_name}
        
        try:
            auth = f"?auth={DB_SECRET}"
            
            # 1. Добавляем чат в список слева (PATCH не затирает старое)
            requests.patch(f"{DB_BASE_URL}/chats/list/{event.chat_id}.json{auth}", json=chat_info)
            
            # 2. Сохраняем само сообщение в общую историю
            msg_payload = {
                "text": event.raw_text,
                "chat_id": event.chat_id,
                "date": str(event.date)
            }
            requests.post(f"{DB_BASE_URL}/messages.json{auth}", json=msg_payload)
            
            logger.info(f"✅ Чат '{chat_name}' обновлен в админке")
        except Exception as e:
            logger.error(f"❌ Ошибка Firebase: {e}")

    logger.info(f"🎬 Запуск по сессии {SESSION_NAME}...")
    await client.connect()
    
    if not await client.is_user_authorized():
        logger.error("❌ СЕССИЯ СДОХЛА!")
        return

    logger.info("✅ Бот в сети! Напиши что-нибудь в ТГ, чтобы чат появился в админке.")
    await client.run_until_disconnected()

@app.route('/')
def health(): return "Status: Active", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    try:
        asyncio.run(telegram_worker())
    except Exception as e:
        logger.error(f"FATAL: {e}")
