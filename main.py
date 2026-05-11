import asyncio
import random
import os
import requests
import logging
from flask import Flask
from threading import Thread
from telethon import TelegramClient, errors

# --- НАСТРОЙКИ ---
API_ID = 38696066
API_HASH = '0018e2c1689dc0a9bb1490a09e14f0cc'
SESSION_NAME = 'session_name' 

DB_SECRET = "03FjyGvc0J1Vr7qcLei0tc0IXNRKEsuZg2Icc3fd"
DB_BASE_URL = "https://typing-939e2-default-rtdb.firebaseio.com"

RUS_LETTERS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
# -------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Глобальные переменные для хранения строк и текущего индекса
messages_list = []
current_index = 0

def load_messages():
    global messages_list
    if os.path.exists('txt.txt'):
        with open('txt.txt', 'r', encoding='utf-8') as f:
            messages_list = [line.strip().lower() for line in f if line.strip()]
        logger.info(f"✅ Загружено строк из txt.txt: {len(messages_list)}")
    else:
        logger.error("❌ Файл txt.txt не найден!")

def modify_text(text):
    """Твоя логика изменения текста"""
    # Вставляем одну случайную русскую букву
    char = random.choice(RUS_LETTERS)
    pos = random.randint(0, len(text))
    text = text[:pos] + char + text[pos:]
    
    # Шанс 40% на вставку /
    if random.random() < 0.40:
        pos_slash = random.randint(0, len(text))
        text = text[:pos_slash] + "/" + text[pos_slash:]
    return text

async def send_next_message(target_id):
    global current_index, messages_list
    
    if not messages_list:
        logger.error("Список сообщений пуст!")
        return

    # Если дошли до конца файла — начинаем сначала
    if current_index >= len(messages_list):
        current_index = 0
        logger.info("🔄 Список пройден, начинаю с первой строки.")

    raw_text = messages_list[current_index]
    final_text = modify_text(raw_text)
    
    try:
        # Статус "Печатает..." и отправка
        async with client.action(int(target_id), 'typing'):
            await asyncio.sleep(0.5) # Небольшая пауза для реалистичности
            await client.send_message(int(target_id), final_text)
            logger.info(f"✅ [Строка {current_index+1}] Отправлено: {final_text}")
            current_index += 1
    except Exception as e:
        logger.error(f"❌ Ошибка отправки: {e}")

async def firebase_listener():
    """Слушаем кнопку ПУСК с сайта"""
    await client.connect()
    if not await client.is_user_authorized():
        logger.error("❌ СЕССИЯ ДОХЛАЯ!")
        return

    load_messages()
    logger.info("✅ Бот в сети. Жду нажатия кнопки на сайте...")
    
    last_trigger = None
    auth = f"?auth={DB_SECRET}"

    while True:
        try:
            # Запрашиваем состояние команд из Firebase
            resp = requests.get(f"{DB_BASE_URL}/commands.json{auth}").json()
            if resp:
                target_id = resp.get('target_id')
                trigger = resp.get('trigger')

                # Если trigger изменился — значит кнопка была нажата
                if trigger and trigger != last_trigger:
                    last_trigger = trigger
                    if target_id:
                        await send_next_message(target_id)
                    else:
                        logger.warning("⚠️ Кнопка нажата, но цель (target_id) не выбрана!")
        except Exception as e:
            logger.error(f"Ошибка связи с Firebase: {e}")
        
        await asyncio.sleep(1) # Проверка раз в секунду

@app.route('/')
def health(): return "Ready", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    client.loop.run_until_complete(firebase_listener())
