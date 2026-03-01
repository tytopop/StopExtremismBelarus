# core/telethon_client.py
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio

async def check_user_subscriptions(user):
    """
    Проверяем подписки конкретного пользователя.
    user = {'user_id': int, 'api_id': int, 'api_hash': str, 'session_data': str}
    Возвращает set с именами каналов/ботов.
    """
    subscriptions = set()
    try:
        async with TelegramClient(StringSession(user['session_data']), user['api_id'], user['api_hash']) as client:
            async for dialog in client.iter_dialogs():
                # Только каналы и супергруппы
                if dialog.is_channel or dialog.is_group:
                    subscriptions.add(dialog.entity.username or dialog.name)
    except Exception as e:
        print(f"❌ Ошибка Telethon для пользователя {user['user_id']}: {e}")
    return subscriptions
