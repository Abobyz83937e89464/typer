import asyncio
import random
import os
import firebase_admin
from firebase_admin import credentials, db
from telethon import TelegramClient, functions, types
from flask import Flask
from threading import Thread

# --- НАСТРОЙКИ ---
API_ID = 38696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
DB_URL = 'https://typing-939e2-default-rtdb.firebaseio.com/'
RUS_CHARS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

app = Flask(__name__)
@app.route('/')
def home(): return "Бот работает"

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})

client = TelegramClient('session_name', API_ID, API_HASH)

def add_noise(text):
    pos = random.randint(0, len(text))
    return text[:pos] + random.choice(RUS_CHARS) + text[pos:]

async def sync_chats():
    """Отправляет список последних 20 чатов в Firebase"""
    print("🔄 Синхронизация чатов...")
    dialogs = await client.get_dialogs(limit=20)
    chat_data = {}
    for d in dialogs:
        chat_data[str(d.id)] = {"name": d.name}
    db.reference('chats/list').set(chat_data)
    print("✅ Список чатов обновлен в базе")

async def send_msg():
    # 1. Получаем ID цели из базы
    target_id = db.reference('commands/target_id').get()
    if not target_id:
        print("❌ Цель не выбрана в интерфейсе")
        return

    # 2. Читаем текст
    if not os.path.exists('txt.txt'): return
    with open('txt.txt', 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    
    if not lines: return
    msg = random.choice(lines).lower()
    msg = add_noise(msg)
    if random.random() < 0.3: msg += "/"

    try:
        # Превращаем ID обратно в число (Firebase хранит ключи как строки)
        entity = await client.get_input_entity(int(target_id))
        async with client.action(entity, 'typing'):
            await asyncio.sleep(0.4)
            await client.send_message(entity, msg)
            print(f"🔥 ПУЛЬНУЛ В {target_id}: {msg}")
    except Exception as e:
        print(f"Ошибка: {e}")

def db_listener(event):
    if event.data:
        asyncio.run_coroutine_threadsafe(send_msg(), bot_loop)

async def start_bot():
    await client.start()
    await sync_chats() # При запуске обновляем список чатов
    db.reference('commands/trigger').listen(db_listener)

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))).start()
    bot_loop = asyncio.get_event_loop()
    bot_loop.create_task(start_bot())
    bot_loop.run_forever()
