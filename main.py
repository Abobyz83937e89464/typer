import asyncio
import random
import os
import logging
import sys
import aiohttp
from flask import Flask
from threading import Thread
from telethon import TelegramClient, errors

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("MORPHEUSOV_ULTRASONIC")

# --- КОНФИГУРАЦИЯ ---
API_ID = 38696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
SESSION_NAME = 'session_name' # Всегда с маленькой, как ты и просил
DB_URL = "https://typing-939e2-default-rtdb.firebaseio.com"

# Автоматическое получение ссылки от Render
SELF_URL = os.environ.get('RENDER_EXTERNAL_URL')

RUS_LETTERS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

app = Flask(__name__)
messages_list = []
current_index = 0

@app.route('/')
def health(): return "SYSTEM: OVERCLOCK_STABLE", 200

def insert_randomly(text, char):
    """Вставляет символ в случайное место в строке"""
    if not text: return char
    pos = random.randint(0, len(text))
    return text[:pos] + char + text[pos:]

def load_messages():
    global messages_list
    if os.path.exists('txt.txt'):
        with open('txt.txt', 'r', encoding='utf-8') as f:
            # Твоя логика: убираем пробелы и в нижний регистр
            messages_list = [line.strip().lower() for line in f if line.strip()]
        logger.info(f"✅ База загружена: {len(messages_list)} строк")

async def pinger():
    """Крон-джоб: сам получает ссылку и пингует её каждые 14 минут"""
    await asyncio.sleep(20) # Даем время серверу подняться
    
    url = SELF_URL
    if not url:
        logger.warning("⚠️ Переменная RENDER_EXTERNAL_URL не найдена. Пингер отключен.")
        return

    logger.info(f"📡 Авто-пингер запущен на адрес: {url}")
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        logger.info("📡 Self-ping: OK (сервер не спит)")
            except Exception as e:
                logger.error(f"📡 Self-ping error: {e}")
            await asyncio.sleep(14 * 60) # Ровно 14 минут

async def bot_worker():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    async def connect_client():
        if not client.is_connected():
            await client.connect()
        return await client.is_user_authorized()

    if not await connect_client():
        logger.error("🚨 SESSION ERROR: Файл сессии битый или не найден")
        return
    
    load_messages()
    last_trigger = None
    
    async with aiohttp.ClientSession() as session:
        logger.info("🔥 БОТ С АВТО-ОШИБКАМИ И ПИНГЕРОМ В СЕТИ")

        while True:
            try:
                if not client.is_connected(): await client.connect()

                # Опрос Firebase
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
                            
                            # ТВОЯ ЛОГИКА ОШИБОК
                            msg = messages_list[current_index]
                            char = random.choice(RUS_LETTERS)
                            final_text = insert_randomly(msg, char)
                            
                            # Шанс 40% на вставку слэша /
                            if random.random() < 0.40:
                                final_text = insert_randomly(final_text, "/")
                            
                            current_index += 1
                            target_peer = int(t_id)

                            try:
                                # Статус "Печатает..."
                                async with client.action(target_peer, 'typing'):
                                    await client.send_message(target_peer, final_text)
                                    logger.info(f"✅ [{final_text}] -> {target_peer}")
                            
                            except errors.FloodWaitError as e:
                                logger.warning(f"⚠️ МУТ! Ждем {e.seconds} сек...")
                                await asyncio.sleep(e.seconds)
                            except Exception as e:
                                logger.error(f"❌ Ошибка: {e}")

                # Синхронизация чатов (кэш сущностей)
                if random.random() < 0.01:
                    dialogs = await client.get_dialogs(limit=15)
                    chat_map = {str(d.id): {"name": d.name} for d in dialogs if d.name}
                    await session.put(f"{DB_URL}/chats/list.json", json=chat_map)

            except Exception as e:
                if "disconnected" not in str(e).lower():
                    logger.error(f"⚠️ Цикл: {e}")
            
            await asyncio.sleep(0.2) # Оптимально для Render

def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Запускаем пингер и воркера в одном цикле
    loop.create_task(pinger())
    loop.run_until_complete(bot_worker())

if __name__ == '__main__':
    # Запуск в фоне
    Thread(target=start_bot, daemon=True).start()
    
    # Порт для Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
