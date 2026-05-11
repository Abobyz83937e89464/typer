import os
import asyncio
import logging
from flask import Flask
from telethon import TelegramClient
import firebase_admin
from firebase_admin import credentials, db

# Настройка логирования (Render подхватит это сразу)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- КОНФИГ ---
API_ID = 24391694
API_HASH = '1f654f6760f9e1e27a6971169c9b7405'
SESSION_NAME = 'session_name' 
DB_URL = 'https://typing-939e2-default-rtdb.firebaseio.com/'

# --- FIREBASE ---
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate('firebase_key.json')
        firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})
        logger.info("✅ Firebase initialized")
    except Exception as e:
        logger.error(f"❌ Firebase error: {e}")

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running. Check Render logs!"

# --- TELEGRAM LOGIC ---
async def telegram_worker():
    logger.info("🎬 Starting Telegram Worker...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error("❌ NOT AUTHORIZED! Session file is missing or invalid.")
            return

        logger.info("✅ Telegram authorized!")
        
        while True:
            logger.info("🔍 Syncing chats...")
            chats_data = {}
            async for dialog in client.iter_dialogs(limit=50):
                chats_data[str(dialog.id)] = {
                    "name": str(dialog.name),
                    "unread": dialog.unread_count
                }
            
            db.reference('chats').set(chats_data)
            db.reference('status').set({"last_sync": "success"})
            logger.info(f"🚀 Synced {len(chats_data)} chats.")
            
            await asyncio.sleep(60)
            
    except Exception as e:
        logger.error(f"❌ Worker error: {e}")

# --- RUN EVERYTHING ---
async def main():
    # Запускаем Flask в фоне (через асинхронную обертку)
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', 10000, app)
    
    logger.info("🌐 Web server starting on port 10000...")
    
    # Запускаем и веб-сервер, и бота одновременно
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, server.serve_forever)
    
    await telegram_worker()

if __name__ == '__main__':
    asyncio.run(main())
