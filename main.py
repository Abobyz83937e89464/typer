import os
import asyncio
import threading
import sys
from flask import Flask
from telethon import TelegramClient
import firebase_admin
from firebase_admin import credentials, db

# --- НАСТРОЙКИ ---
API_ID = 24391694
API_HASH = '1f654f6760f9e1e27a6971169c9b7405'
SESSION_NAME = 'session_name' 
DB_URL = 'https://typing-939e2-default-rtdb.firebaseio.com/'

# Функция для принудительного логирования
def log(message):
    print(message, flush=True)
    sys.stdout.flush()

# --- ИНИЦИАЛИЗАЦИЯ FIREBASE ---
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate('firebase_key.json')
        firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})
        log("✅ [FIREBASE] Подключение успешно")
    except Exception as e:
        log(f"❌ [FIREBASE] Ошибка: {e}")

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот активен. Смотри логи!"

async def sync_logic():
    log("🎬 [SYSTEM] Фоновый цикл запущен!")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            log("❌ [TELEGRAM] СЕССИЯ НЕ ВАЛИДНА!")
            db.reference('status').set({"auth": "failed"})
            return

        log("✅ [TELEGRAM] Авторизация ОК")
        
        while True:
            log("🔍 [SYNC] Начинаю сбор...")
            chats_data = {}
            async for dialog in client.iter_dialogs(limit=50):
                chats_data[str(dialog.id)] = {
                    "name": str(dialog.name),
                    "unread": dialog.unread_count
                }
            
            db.reference('chats').set(chats_data)
            db.reference('status').set({"last_sync": "ok", "count": len(chats_data)})
            log(f"🚀 [SYNC] Готово! Чатов: {len(chats_data)}")
            await asyncio.sleep(60)
            
    except Exception as e:
        log(f"❌ [CRITICAL] Ошибка: {e}")

def start_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(sync_logic())

# Запуск потока
threading.Thread(target=start_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
