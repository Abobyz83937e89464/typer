import asyncio
import random
import os
import requests
import logging
import sys
from flask import Flask
from threading import Thread
from telethon import TelegramClient

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("TURBO_BOT")

# --- КОНФИГУРАЦИЯ ---
API_ID = 38696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
SESSION_NAME = 'session_name'
DB_URL = "https://typing-939e2-default-rtdb.firebaseio.com"

app = Flask(__name__)
messages_list = []
current_index = 0

@app.route('/')
def health(): return "OK", 200

def load_messages():
    global messages_list
    if os.path.exists('txt.txt'):
        with open('txt.txt', 'r', encoding='utf-8') as f:
            messages_list = [line.strip() for line in f if line.strip()]
        logger.info(f"✅ Загружено строк: {len(messages_list)}")

async def bot_worker():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        logger.error("🚨 СЕССИЯ НЕ РАБОТАЕТ!")
        return
    
    load_messages()
    last_trigger = None
    
    # Создаем сессию для мгновенных HTTP-запросов
    session = requests.Session()
    
    logger.info("🚀 ТУРБО-РЕЖИМ АКТИВИРОВАН")

    while True:
        try:
            # Опрашиваем Firebase
            resp = session.get(f"{DB_URL}/commands.json", timeout=0.5).json()
            if resp:
                t_id = resp.get('target_id')
                trig = resp.get('trigger')
                
                if trig and trig != last_trigger:
                    last_trigger = trig
                    if t_id and messages_list:
                        global current_index
                        if current_index >= len(messages_list): current_index = 0
                        msg = messages_list[current_index]
                        current_index += 1
                        
                        # Мгновенная отправка без лишних пауз
                        asyncio.create_task(client.send_message(int(t_id), msg))
                        logger.info(f"⚡ Пуля улетела в {t_id}")

            # Редкая синхронизация чатов (раз в 30 сек), чтобы не грузить поток
            if random.random() < 0.01:
                dialogs = await client.get_dialogs(limit=10)
                chats = {str(d.id): {"name": d.name} for d in dialogs if d.name}
                session.put(f"{DB_URL}/chats/list.json", json=chats, timeout=1)

        except Exception as e:
            logger.error(f"Ошибка: {e}")
        
        await asyncio.sleep(0.2) # 200мс — это ОЧЕНЬ быстро

def start_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_worker())

if __name__ == '__main__':
    # Бот в фоне
    t = Thread(target=start_bot_thread, daemon=True)
    t.start()
    
    # Flask для Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
