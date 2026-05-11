import asyncio
import random
import os
import logging
import sys
import aiohttp
from flask import Flask
from threading import Thread
from telethon import TelegramClient

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("ULTRASONIC_TYPER")

# --- КОНФИГУРАЦИЯ ---
API_ID = 38696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
SESSION_NAME = 'session_name'
DB_URL = "https://typing-939e2-default-rtdb.firebaseio.com"

app = Flask(__name__)
messages_list = []
current_index = 0

@app.route('/')
def health(): return "SYSTEM: OVERCLOCK", 200

def load_messages():
    global messages_list
    if os.path.exists('txt.txt'):
        with open('txt.txt', 'r', encoding='utf-8') as f:
            messages_list = [line.strip() for line in f if line.strip()]

async def bot_worker():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        logger.error("🚨 SESSION ERROR")
        return
    
    load_messages()
    last_trigger = None
    
    # Используем одну асинхронную сессию для всех запросов
    async with aiohttp.ClientSession() as session:
        logger.info("🚀 ГИПЕРЗВУК ЗАПУЩЕН")

        while True:
            try:
                # Опрос базы каждые 0.1 сек (максимальный разгон)
                async with session.get(f"{DB_URL}/commands.json", timeout=0.5) as resp:
                    data = await resp.json()
                
                if data:
                    t_id = data.get('target_id')
                    trig = data.get('trigger')

                    if trig and trig != last_trigger:
                        last_trigger = trig
                        if t_id and messages_list:
                            global current_index
                            if current_index >= len(messages_list): current_index = 0
                            msg = messages_list[current_index]
                            current_index += 1
                            
                            # Мгновенный выстрел в фон без ожидания
                            try:
                                asyncio.create_task(client.send_message(int(t_id), msg))
                                logger.info(f"⚡ [0.1s] SENT -> {t_id}")
                            except:
                                # Если юзер новый, придется подождать поиска
                                entity = await client.get_entity(int(t_id))
                                await client.send_message(entity, msg)

                # Редкая синхронизация (раз в 100 циклов), чтобы не мешать скорости
                if random.random() < 0.01:
                    dialogs = await client.get_dialogs(limit=10)
                    chat_map = {str(d.id): {"name": d.name} for d in dialogs if d.name}
                    async with session.put(f"{DB_URL}/chats/list.json", json=chat_map) as r:
                        pass

            except Exception:
                pass # Игнорим любые ошибки сети ради скорости
            
            await asyncio.sleep(0.1) # ВОТ ОНО — 100 миллисекунд

def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_worker())

if __name__ == '__main__':
    Thread(target=start_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
