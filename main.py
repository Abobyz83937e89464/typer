import asyncio
import random
import os
import requests
import logging
from flask import Flask
from threading import Thread
from telethon import TelegramClient, errors

# --- КОНФИГУРАЦИЯ ---
API_ID = 38696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
SESSION_NAME = 'Session_name' 

DB_SECRET = "03FjyGvc0J1Vr7qcLei0tc0IXNRKEsuZg2Icc3fd"
DB_BASE_URL = "https://typing-939e2-default-rtdb.firebaseio.com"
RUS_LETTERS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
# -------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

messages_list = []
current_index = 0

def load_messages():
    global messages_list
    if os.path.exists('txt.txt'):
        with open('txt.txt', 'r', encoding='utf-8') as f:
            messages_list = [line.strip().lower() for line in f if line.strip()]
        logger.info(f"✅ Загружено строк: {len(messages_list)}")
    else:
        logger.error("❌ Файл txt.txt отсутствует!")

def modify_text(text):
    char = random.choice(RUS_LETTERS)
    pos = random.randint(0, len(text))
    text = text[:pos] + char + text[pos:]
    if random.random() < 0.40:
        pos_slash = random.randint(0, len(text))
        text = text[:pos_slash] + "/" + text[pos_slash:]
    return text

async def sync_dialogs():
    """Обновление списка чатов в Firebase каждые 30 секунд"""
    auth = f"?auth={DB_SECRET}"
    while True:
        try:
            if client.is_connected() and await client.is_user_authorized():
                dialogs = await client.get_dialogs(limit=25)
                chat_data = {str(d.id): {"name": d.name} for d in dialogs if d.name}
                requests.put(f"{DB_BASE_URL}/chats/list.json{auth}", json=chat_data)
                logger.info("🔄 Список чатов синхронизирован с базой.")
        except Exception as e:
            logger.error(f"Ошибка синхронизации: {e}")
        await asyncio.sleep(30)

async def firebase_listener():
    """Слушаем команды ПУСК с сайта"""
    await client.connect()
    if not await client.is_user_authorized():
        logger.error("❌ СЕССИЯ ДОХЛАЯ!")
        return

    load_messages()
    # Запускаем синхронизацию чатов в фоне
    asyncio.create_task(sync_dialogs())
    
    last_trigger = None
    auth = f"?auth={DB_SECRET}"

    while True:
        try:
            resp = requests.get(f"{DB_BASE_URL}/commands.json{auth}", timeout=10).json()
            if resp:
                target_id = resp.get('target_id')
                trigger = resp.get('trigger')

                if trigger and trigger != last_trigger:
                    last_trigger = trigger
                    if target_id and messages_list:
                        if current_index >= len(messages_list):
                            globals()['current_index'] = 0
                        
                        raw_text = messages_list[current_index]
                        final_text = modify_text(raw_text)
                        
                        async with client.action(int(target_id), 'typing'):
                            await asyncio.sleep(0.3)
                            await client.send_message(int(target_id), final_text)
                            logger.info(f"🚀 Отправлено: {final_text}")
                            globals()['current_index'] += 1
        except Exception as e:
            logger.error(f"Ошибка FB: {e}")
        await asyncio.sleep(1)

@app.route('/')
def health(): return "Status: OK", 200

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    client.loop.run_until_complete(firebase_listener())
