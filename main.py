import os
import json
import logging
import asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events
import firebase_admin
from firebase_admin import credentials, db

# 1. Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 2. Конфигурация (замени своими данными)
API_ID = 1234567  # Твой API ID
API_HASH = 'твой_api_hash'
SESSION_NAME = 'session_name' # Убедись, что файл .session загружен
DATABASE_URL = 'https://твой-проект.firebaseio.com/' 

app = Flask(__name__)

# 3. Инициализация Firebase с защитой от ошибок JWT
def init_firebase():
    try:
        # Пробуем взять конфиг из переменной окружения Render
        config_raw = os.environ.get('FIREBASE_CONFIG')
        
        if config_raw:
            config_dict = json.loads(config_raw)
            # Критически важно: чистим переносы строк в ключе
            if 'private_key' in config_dict:
                config_dict['private_key'] = config_dict['private_key'].replace('\\n', '\n')
            cred = credentials.Certificate(config_dict)
            logger.info("✅ Firebase: инициализация через Environment Variable")
        else:
            # Если переменной нет, ищем файл
            cred = credentials.Certificate('firebase_key.json')
            logger.info("✅ Firebase: инициализация через файл")

        firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
        return True
    except Exception as e:
        logger.error(f"❌ Firebase Error: {e}")
        return False

# 4. Telegram Worker
async def telegram_worker():
    if not init_firebase():
        logger.error("🚫 Останавливаю воркер: Firebase не запущен")
        return

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            # Пример записи сообщения в базу
            ref = db.reference('messages')
            ref.push({
                'text': event.raw_text,
                'sender_id': event.sender_id,
                'chat_id': event.chat_id
            })
            logger.info(f"📩 Сообщение сохранено: {event.raw_text[:20]}...")
        except Exception as e:
            logger.error(f"❌ Ошибка записи в DB: {e}")

    logger.info("🎬 Запуск Telegram клиента...")
    await client.start()
    logger.info("✅ Telegram авторизован!")
    await client.run_until_disconnected()

# 5. Web Server (Flask)
@app.route('/')
def health_check():
    return "Service is running", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 6. Точка входа
if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем Telegram в основном потоке через asyncio
    try:
        asyncio.run(telegram_worker())
    except KeyboardInterrupt:
        pass
