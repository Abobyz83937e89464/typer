import os
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient
import firebase_admin
from firebase_admin import credentials, db

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
        print("✅ [FIREBASE] Подключение успешно")
    except Exception as e:
        print(f"❌ [FIREBASE] Ошибка: {e}")

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот активен. Проверь логи Render для статуса синхронизации."

# --- ЛОГИКА ТЕЛЕГРАМА ---
async def sync_logic():
    print("🎬 [SYSTEM] Запуск фонового цикла синхронизации...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ [TELEGRAM] СЕССИЯ НЕ ВАЛИДНА! Бот не может войти.")
            db.reference('status').set({"auth": "failed", "error": "Session invalid"})
            return

        print("✅ [TELEGRAM] Авторизация пройдена успешно!")
        
        while True:
            print("🔍 [SYNC] Сбор чатов...")
            chats_data = {}
            async for dialog in client.iter_dialogs(limit=50): # Для теста берем первые 50
                chats_data[str(dialog.id)] = {
                    "name": dialog.name or "Unknown",
                    "unread": dialog.unread_count
                }
            
            db.reference('chats').set(chats_data)
            db.reference('status').set({"last_sync": "success", "count": len(chats_data)})
            print(f"🚀 [SYNC] База обновлена! Найдено чатов: {len(chats_data)}")
            
            await asyncio.sleep(60)
            
    except Exception as e:
        print(f"❌ [CRITICAL] Ошибка в цикле: {e}")
        db.reference('errors').push({"msg": str(e)})

def start_background_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(sync_logic())

# Запускаем поток с ботом ПРИНУДИТЕЛЬНО при старте Flask
# Это сработает даже под Gunicorn
thread = threading.Thread(target=start_background_loop, daemon=True)
thread.start()

if __name__ == '__main__':
    # Это для локального запуска
    app.run(host='0.0.0.0', port=10000)
