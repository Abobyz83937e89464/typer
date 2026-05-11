import asyncio
import random
import os
import requests
import logging
import sys
from flask import Flask
from threading import Thread
from telethon import TelegramClient

# Настройка логов для Render
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("RENDER_BOT")

# --- КОНФИГУРАЦИЯ ---
API_ID = 38696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
SESSION_NAME = 'session_name' # Файл Session_name.session должен быть в корне!

DB_SECRET = "03FjyGvc0J1Vr7qcLei0tc0IXNRKEsuZg2Icc3fd"
DB_BASE_URL = "https://typing-939e2-default-rtdb.firebaseio.com"
RUS_LETTERS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

app = Flask(__name__)
messages_list = []

@app.route('/')
def health():
    return "SERVER IS ALIVE", 200

def load_messages():
    global messages_list
    if os.path.exists('txt.txt'):
        with open('txt.txt', 'r', encoding='utf-8') as f:
            messages_list = [line.strip() for line in f if line.strip()]
        logger.info(f"✅ txt.txt загружен ({len(messages_list)} строк)")
    else:
        logger.error("❌ txt.txt НЕ НАЙДЕН")

async def bot_worker():
    """Основная логика бота в отдельном потоке"""
    logger.info("🤖 Запуск фонового воркера...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error("🚨 СЕССИЯ НЕ АВТОРИЗОВАНА! Проверь файл .session")
            return
        
        logger.info("✅ Telegram подключен!")
        load_messages()
        
        last_trigger = None
        auth = f"?auth={DB_SECRET}"

        while True:
            try:
                # 1. Синхронизируем чаты (раз в 15 сек для экономии)
                dialogs = await client.get_dialogs(limit=25)
                chat_data = {str(d.id): {"name": d.name} for d in dialogs if d.name}
                requests.put(f"{DB_BASE_URL}/chats/list.json{auth}", json=chat_data, timeout=5)

                # 2. Проверяем команды с сайта
                resp = requests.get(f"{DB_BASE_URL}/commands.json{auth}", timeout=5).json()
                if resp:
                    target_id = resp.get('target_id')
                    trigger = resp.get('trigger')

                    if trigger and trigger != last_trigger:
                        last_trigger = trigger
                        if target_id and messages_list:
                            msg = random.choice(messages_list)
                            async with client.action(int(target_id), 'typing'):
                                await asyncio.sleep(0.4)
                                await client.send_message(int(target_id), msg)
                                logger.info(f"🚀 Отправлено в {target_id}: {msg[:20]}...")
            
            except Exception as e:
                logger.error(f"⚠️ Ошибка в цикле: {e}")
            
            await asyncio.sleep(2)
            
    except Exception as e:
        logger.error(f"💥 Критическая ошибка воркера: {e}")

def start_bot():
    """Запуск asyncio в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_worker())

if __name__ == '__main__':
    # Сначала запускаем бота в фоне
    bot_thread = Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask в основном потоке (Render это любит)
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Flask стартует на порту {port}...")
    app.run(host='0.0.0.0', port=port)
