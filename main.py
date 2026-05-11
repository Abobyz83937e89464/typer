import os
import asyncio
import threading
import logging
from flask import Flask
from telethon import TelegramClient
import firebase_admin
from firebase_admin import credentials, db

# Настройка логирования, чтобы Render всё видел
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- НАСТРОЙКИ ---
API_ID = 24391694
API_HASH = '1f654f6760f9e1e27a6971169c9b7405'
SESSION_NAME = 'session_name' 
DB_URL = 'https://typing-939e2-default-rtdb.firebaseio.com/'

# --- ИНИЦИАЛИЗАЦИЯ FIREBASE ---
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate('firebase_key.json')
        firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})
        logger.info("✅ [FIREBASE] Connected")
    except Exception as e:
        logger.error(f"❌ [FIREBASE] Error: {e}")

app = Flask(__name__)

@app.route('/')
def home():
    return "Status: OK. Check logs for sync info."

async def run_bot():
    logger.info("🎬 [SYSTEM] Starting Telegram sync loop...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error("❌ [TELEGRAM] SESSION INVALID! Need new .session file.")
            db.reference('status').set({"auth": "failed", "msg": "Need session"})
            return

        logger.info("✅ [TELEGRAM] Authorized!")
        
        while True:
            logger.info("🔍 [SYNC] Fetching chats...")
            chats_data = {}
            async for dialog in client.iter_dialogs(limit=50):
                chats_data[str(dialog.id)] = {
                    "name": str(dialog.name),
                    "unread": dialog.unread_count
                }
            
            db.reference('chats').set(chats_data)
            db.reference('status').set({"last_sync": "success", "count": len(chats_data)})
            logger.info(f"🚀 [SYNC] Success! Chats: {len(chats_data)}")
            
            await asyncio.sleep(60) # Ждем минуту до следующей синхронизации
            
    except Exception as e:
        logger.error(f"❌ [CRITICAL] Sync error: {e}")

# Функция-обертка для запуска в отдельном потоке
def start_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

# Запускаем один раз при старте
threading.Thread(target=start_bot_thread, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
