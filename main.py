import asyncio
import random
import os
import requests
import logging
import sys
from flask import Flask
from threading import Thread
from telethon import TelegramClient

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("NEO_TYPER")

# --- КОНФИГУРАЦИЯ ---
API_ID = 38696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
SESSION_NAME = 'session_name'  # Теперь строго с маленькой!

DB_URL = "https://typing-939e2-default-rtdb.firebaseio.com"

app = Flask(__name__)
messages_list = []
current_index = 0

@app.route('/')
def health():
    return "STATUS: ACTIVE", 200

def load_messages():
    global messages_list
    if os.path.exists('txt.txt'):
        with open('txt.txt', 'r', encoding='utf-8') as f:
            messages_list = [line.strip() for line in f if line.strip()]
        logger.info(f"✅ База загружена: {len(messages_list)} строк")
    else:
        logger.error("❌ Файл txt.txt не найден!")

async def bot_worker():
    # Проверка наличия файла сессии перед стартом
    if not os.path.exists(f"{SESSION_NAME}.session"):
        logger.error(f"🚨 ФАЙЛ {SESSION_NAME}.session НЕ НАЙДЕН! Бот не запустится.")
        return

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error("🚨 ОШИБКА: Сессия не авторизована. Пересоздай файл .session")
            return
        
        logger.info("✅ Telegram подключен. Турбо-режим готов!")
        load_messages()
        
        last_trigger = None
        http_session = requests.Session()

        while True:
            try:
                # Опрос Firebase (чуть увеличили таймаут для стабильности)
                resp = http_session.get(f"{DB_URL}/commands.json", timeout=1.5).json()
                
                if resp:
                    t_id = resp.get('target_id')
                    trig = resp.get('trigger')

                    if trig and trig != last_trigger:
                        last_trigger = trig
                        if t_id and messages_list:
                            global current_index
                            if current_index >= len(messages_list):
                                current_index = 0
                            
                            msg = messages_list[current_index]
                            current_index += 1
                            
                            # Умная отправка: решаем проблему "Input Entity"
                            try:
                                # Сначала пытаемся отправить по быстрому кэшу
                                await client.send_message(int(t_id), msg)
                                logger.info(f"⚡ Пуля улетела в {t_id}")
                            except ValueError:
                                # Если ID новый, принудительно ищем сущность
                                logger.info(f"🔍 Поиск нового чата {t_id}...")
                                entity = await client.get_entity(int(t_id))
                                await client.send_message(entity, msg)
                                logger.info(f"⚡ Пуля улетела после поиска в {t_id}")

                # Синхронизация списка чатов раз в ~30 секунд
                if random.random() < 0.03:
                    dialogs = await client.get_dialogs(limit=20)
                    chat_map = {str(d.id): {"name": d.name} for d in dialogs if d.name}
                    http_session.put(f"{DB_URL}/chats/list.json", json=chat_map, timeout=2)

            except Exception as e:
                if "timeout" not in str(e).lower():
                    logger.error(f"⚠️ Ошибка цикла: {e}")
            
            await asyncio.sleep(0.3) # Скорость отклика

    except Exception as e:
        logger.error(f"💥 Критическая ошибка бота: {e}")

def run_bot_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_worker())

if __name__ == '__main__':
    # Запуск бота в фоновом потоке
    bot_thread = Thread(target=run_bot_in_thread, daemon=True)
    bot_thread.start()
    
    # Запуск Flask сервера (основной поток для Render)
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 Сервер запущен на порту {port}")
    app.run(host='0.0.0.0', port=port)
