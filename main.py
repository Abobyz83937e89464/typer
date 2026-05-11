import os
import asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient
import firebase_admin
from firebase_admin import credentials, db

# --- НАСТРОЙКИ ---
API_ID = 24391694  # Твой API ID
API_HASH = '1f654f6760f9e1e27a6971169c9b7405'
SESSION_NAME = 'session_name' # Убедись, что файл .session лежит в корне
DB_URL = 'https://typing-939e2-default-rtdb.firebaseio.com/'

# --- ИНИЦИАЛИЗАЦИЯ FIREBASE ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate('firebase_key.json')
        firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})
    print("✅ [FIREBASE] Подключение успешно установлено")
except Exception as e:
    print(f"❌ [FIREBASE] Ошибка инициализации: {e}")

# --- FLASK (для Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает и логирует данные."

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- ЛОГИКА ТЕЛЕГРАМА ---
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def sync_chats():
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ [TELEGRAM] Ошибка: Сессия не авторизована! Залей актуальный .session файл.")
        return

    print("✅ [TELEGRAM] Бот успешно авторизован")

    while True:
        try:
            print("🔍 [SYNC] Начинаю сбор чатов...")
            chats_data = {}
            count = 0
            
            async for dialog in client.iter_dialogs():
                # Собираем только группы и супергруппы для примера
                if dialog.is_group or dialog.is_channel:
                    chats_data[str(dialog.id)] = {
                        "name": dialog.name,
                        "unread_count": dialog.unread_count
                    }
                    count += 1
            
            if chats_data:
                db.reference('chats').set(chats_data)
                print(f"🚀 [SYNC] Успешно! Загружено чатов: {count}")
            else:
                print("⚠️ [SYNC] Чаты не найдены. Проверь аккаунт.")
                db.reference('status').set({"error": "No chats found", "time": "now"})

        except Exception as e:
            print(f"❌ [SYNC] Критическая ошибка при обновлении базы: {e}")
            try:
                db.reference('errors').push({"msg": str(e)})
            except:
                pass
        
        await asyncio.sleep(60) # Обновление раз в минуту

async def main():
    print("🎬 Запуск основного цикла...")
    await sync_chats()

if __name__ == '__main__':
    # Запускаем веб-сервер в отдельном потоке
    Thread(target=run_flask).start()
    
    # Запускаем Телеграм
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
