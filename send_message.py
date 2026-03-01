#!/usr/bin/env python3
import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')

async def send_message():
    # Создание клиента с сессией босса
    client = TelegramClient('boss_session', API_ID, API_HASH)
    
    await client.start()
    print("🤖 Telethon клиент запущен")
    
    try:
        # Отправка сообщения жене
        username = 'Alchernush'  # без @
        message = """Привет, дорогая! 💕

Это сообщение через моего AI ассистента Гарольда 🤖

Он составил нам детальный план поездки на Фукуок с учетом того, что 17 февраля там Тэт (Вьетнамский Новый год)! 

Будет незабываемо:
- Канатная дорога над морем
- Safari и аквапарк 
- Морская рыбалка
- Фейерверки на Новый год!

Вылет завтра в 21:50, готовься! ✈️🏝️"""

        await client.send_message(username, message)
        print(f"✅ Сообщение отправлено @{username}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(send_message())