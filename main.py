import asyncio
import random
import os
import logging
import sys
from flask import Flask
from threading import Thread
from telethon import TelegramClient
import firebase_admin
from firebase_admin import credentials, db

# Логи
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("FAST_BOT")

# --- КОНФИГУРАЦИЯ ---
API_ID = 38696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
SESSION_NAME = 'Session_name'

# Инициализация Firebase через Admin SDK (для Realtime обновлений)
# Если у тебя нет файла ключа, мы будем использовать упрощенный метод через loop
DB_URL = "https://typing-939e2-default-rtdb.firebaseio.com/"

app = Flask(__name__)
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
messages_list = []
current_index = 0

@app.route('/')
def health(): return "FAST_BOT_ALIVE", 200

def load_messages():
    global messages_list
    if os.path.exists('txt.txt'):
        with open('txt.txt', 'r', encoding='utf-8') as f:
            messages_list = [line.strip() for line in f if line.strip()]

async def send_msg(target_id):
    """Функция мгновенной отправки"""
    global current_index
    if not messages_list: return
    
    try:
        if current_index >= len(messages_list): current_index = 0
        msg = messages_list[current_index]
        
        # Уменьшил задержку эмуляции печати до минимума
        async with client.action(int(target_id), 'typing'):
            await asyncio.sleep(0.1) 
            await client.send_message(int(target_id), msg)
            logger.info(f"🚀 МГНОВЕННО: {msg[:15]}")
            current_index += 1
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

async def bot_worker():
    await client.connect()
    if not await client.is_user_authorized():
        logger.error("🚨 НЕТ АВТОРИЗАЦИИ")
        return
    
    load_messages()
    logger.info("✅ Бот готов к моментальной работе")

    last_trigger = None
    
    # Чтобы убрать задержку без Admin SDK, уменьшаем цикл до 0.3 сек
    # Это "агрессивный" опрос, но он дает почти мгновенную реакцию
    while True:
        try:
            # Используем сессию для ускорения запросов
            import requests
            s = requests.Session()
            resp = s.get(f"{DB_URL}/commands.json", timeout=1).json()
            
            if resp:
                t_id = resp.get('target_id')
                trig = resp.get('trigger')
                
                if trig and trig != last_trigger:
                    last_trigger = trig
                    if t_id:
                        # Запускаем отправку без ожидания
                        asyncio.create_task(send_msg(t_id))
            
            # Также синхронизируем чаты, но редко (раз в минуту), чтоб не тормозить основной цикл
            if random.random() < 0.05: 
                dialogs = await client.get_dialogs(limit=15)
                chat_data = {str(d.id): {"name": d.name} for d in dialogs if d.name}
                s.put(f"{DB_URL}/chats/list.json", json=chat_data, timeout=2)

        except Exception as e:
            pass
        
        await asyncio.sleep(0.3) # Задержка всего 300мс — это глазом не моргнешь

def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_worker())

if __name__ == '__main__':
    Thread(target=start_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
