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
logger = logging.getLogger("SUPER_TYPER")

# --- КОНФИГУРАЦИЯ ---
API_ID = 38696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
SESSION_NAME = 'session_name'
DB_URL = "https://typing-939e2-default-rtdb.firebaseio.com"

app = Flask(__name__)
messages_list = []
current_index = 0

@app.route('/')
def health(): return "STATUS: OVERCLOCK_ACTIVE", 200

def load_messages():
    global messages_list
    if os.path.exists('txt.txt'):
        with open('txt.txt', 'r', encoding='utf-8') as f:
            messages_list = [line.strip() for line in f if line.strip()]

async def bot_worker():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    # Функция для безопасного подключения
    async def connect_client():
        if not client.is_connected():
            await client.connect()
        if not await client.is_user_authorized():
            logger.error("🚨 SESSION EXPIRED")
            return False
        return True

    if not await connect_client(): return
    
    load_messages()
    last_trigger = None
    
    async with aiohttp.ClientSession() as session:
        logger.info("🚀 ГИПЕРЗВУК С АВТОРЕКОННЕКТОМ ЗАПУЩЕН")

        while True:
            try:
                # Проверка связи перед каждым циклом
                if not client.is_connected():
                    logger.info("🔄 Переподключение к Telegram...")
                    await client.connect()

                # Опрос базы
                async with session.get(f"{DB_URL}/commands.json", timeout=1.0) as resp:
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
                            
                            # Отправляем напрямую (await), чтобы видеть ошибки сразу
                            try:
                                await client.send_message(int(t_id), msg)
                                logger.info(f"⚡ [HIT] -> {t_id}")
                            except ValueError:
                                # Если юзер новый
                                entity = await client.get_entity(int(t_id))
                                await client.send_message(entity, msg)
                            except ConnectionError:
                                logger.warning("⚠️ Потеря связи, пробую переподключиться...")
                                await client.connect()

                # Синхронизация списка чатов
                if random.random() < 0.01:
                    dialogs = await client.get_dialogs(limit=10)
                    chat_map = {str(d.id): {"name": d.name} for d in dialogs if d.name}
                    await session.put(f"{DB_URL}/chats/list.json", json=chat_map)

            except Exception as e:
                if "disconnected" in str(e).lower():
                    try: await client.connect()
                    except: pass
            
            await asyncio.sleep(0.2) # Вернул 0.2с для стабильности, 0.1с часто рвет связь

def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_worker())

if __name__ == '__main__':
    Thread(target=start_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
