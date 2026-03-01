"""
Модуль мониторинга подписок пользователей на запрещённые Telegram-ресурсы
С ПОДТВЕРЖДЕНИЕМ ОТПИСКИ и INLINE-КНОПКАМИ
"""
from telethon import TelegramClient
from telethon.sessions import StringSession
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from db.database import get_all_users
from core.banned_resources import get_banned_set
from utils.crypto import decrypt_session
from utils.logger import monitor_logger
import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

# Хранилище последних найденных нарушений (для отслеживания отписок)
VIOLATIONS_FILE = "downloads/user_violations.json"


def load_violations():
    """Загружает предыдущие нарушения из файла"""
    if os.path.exists(VIOLATIONS_FILE):
        with open(VIOLATIONS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_violations(violations):
    """Сохраняет нарушения в файл"""
    with open(VIOLATIONS_FILE, 'w') as f:
        json.dump(violations, f, indent=2)


async def check_user_subscriptions(client: TelegramClient, banned_set: set, user_id: int) -> list:
    """
    Проверяет подписки пользователя и возвращает список запрещённых.
    ТОЛЬКО ТОЧНЫЕ СОВПАДЕНИЯ!
    """
    forbidden = []
    try:
        async for dialog in client.iter_dialogs():
            if dialog.is_channel or dialog.is_group:
                entity = dialog.entity

                username = getattr(entity, 'username', None)
                username_lower = username.lower() if username else None

                title = getattr(entity, 'title', None)
                entity_id = str(entity.id)

                # ПРОВЕРКА 1: Точное совпадение username
                if username_lower and username_lower in banned_set:
                    forbidden.append({
                        'name': f"@{username}",
                        'type': 'username',
                        'title': title,
                        'id': entity_id,
                        'username': username
                    })
                    monitor_logger.warning(f"🚨 Запрещён: @{username}")
                    continue

                # ПРОВЕРКА 2: Точное совпадение ID
                if f"id_{entity_id}" in banned_set:
                    forbidden.append({
                        'name': f"ID: {entity_id}",
                        'type': 'id',
                        'title': title,
                        'id': entity_id,
                        'username': username
                    })
                    monitor_logger.warning(f"🚨 Запрещён по ID: {entity_id}")
                    continue

    except Exception as e:
        monitor_logger.error(f"❌ Ошибка проверки подписок: {e}")

    return forbidden


async def send_notification_with_buttons(user_id: int, forbidden: list):
    """
    Отправляет уведомление с INLINE-КНОПКАМИ для каждого запрещённого канала
    """
    try:
        bot = Bot(token=BOT_TOKEN)
        
        for res in forbidden:
            title_display = res['title'] if res['title'] else "Без названия"
            
            message = (
                f"🚨 <b>ОБНАРУЖЕН ЗАПРЕЩЁННЫЙ РЕСУРС!</b>\n\n"
                f"📝 Название: <b>{title_display}</b>\n"
                f"🔗 {res['name']}\n\n"
                f"⚠️ <b>Срочно покиньте этот канал!</b>\n"
                f"После отписки бот автоматически подтвердит."
            )
            
            # Inline-кнопки
            keyboard = []
            
            # Если есть username - кнопка для перехода
            if res.get('username'):
                keyboard.append([
                    InlineKeyboardButton(
                        "📱 Открыть канал", 
                        url=f"https://t.me/{res['username']}"
                    )
                ])
            
            # Кнопка "Проверить снова"
            keyboard.append([
                InlineKeyboardButton(
                    "🔄 Я отписался, проверить снова", 
                    callback_data=f"recheck_{user_id}"
                )
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            await asyncio.sleep(1)
        
        monitor_logger.info(f"✅ Уведомления с кнопками отправлены пользователю {user_id}")
        return True
        
    except Exception as e:
        monitor_logger.error(f"❌ Ошибка отправки через бота: {e}")
        return False


async def send_all_clear_notification(user_id: int):
    """
    Отправляет подтверждение что все запрещённые каналы покинуты
    """
    try:
        bot = Bot(token=BOT_TOKEN)
        
        message = (
            "✅ <b>ОТЛИЧНО!</b>\n\n"
            "🎉 Вы больше не подписаны на запрещённые ресурсы!\n\n"
            "Система продолжает автоматический мониторинг каждые 10 минут."
        )
        
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='HTML'
        )
        
        monitor_logger.info(f"✅ Подтверждение 'всё чисто' отправлено пользователю {user_id}")
        return True
        
    except Exception as e:
        monitor_logger.error(f"❌ Ошибка отправки подтверждения: {e}")
        return False


async def monitor_single_user(user: dict):
    """
    Проверяет подписки одного пользователя.
    Отслеживает изменения и подтверждает отписки.
    """
    client = None
    user_id = user['user_id']
    
    try:
        session_data = decrypt_session(user['session_data'])
        client = TelegramClient(
            StringSession(session_data),
            user['api_id'],
            user['api_hash']
        )

        await client.connect()

        if not await client.is_user_authorized():
            monitor_logger.warning(f"⚠️ Пользователь {user_id} не авторизован")
            return

        banned_set = get_banned_set()

        if not banned_set:
            monitor_logger.warning("⚠️ Список запрещённых ресурсов пуст!")
            return

        # Проверяем подписки
        forbidden = await check_user_subscriptions(client, banned_set, user_id)
        
        # Загружаем предыдущие нарушения
        all_violations = load_violations()
        prev_violations = set(all_violations.get(str(user_id), []))
        
        # Текущие нарушения
        current_violations = set([f"{res['type']}:{res['id']}" for res in forbidden])
        
        # Новые нарушения (появились)
        new_violations = current_violations - prev_violations
        
        # Исправленные нарушения (исчезли)
        fixed_violations = prev_violations - current_violations
        
        # Отправляем уведомления о НОВЫХ нарушениях
        if new_violations:
            new_forbidden = [res for res in forbidden if f"{res['type']}:{res['id']}" in new_violations]
            monitor_logger.info(f"🔔 У пользователя {user_id} найдено {len(new_forbidden)} НОВЫХ запрещённых подписок")
            await send_notification_with_buttons(user_id, new_forbidden)
        
        # Подтверждаем если ВСЕ нарушения исправлены
        if prev_violations and not current_violations:
            monitor_logger.info(f"🎉 Пользователь {user_id} исправил ВСЕ нарушения!")
            await send_all_clear_notification(user_id)
        
        # Сохраняем текущее состояние
        all_violations[str(user_id)] = list(current_violations)
        save_violations(all_violations)
        
        if not forbidden:
            monitor_logger.info(f"✅ У пользователя {user_id} запрещённых подписок не найдено")

    except Exception as e:
        monitor_logger.error(f"❌ Ошибка мониторинга пользователя {user_id}: {e}")
    finally:
        if client and client.is_connected():
            await client.disconnect()


async def monitor_all_users_once():
    """
    Однократная проверка всех пользователей (вызывается планировщиком).
    """
    monitor_logger.info("🔍 Начало проверки подписок всех пользователей...")

    users = await get_all_users()

    if not users:
        monitor_logger.info("ℹ️ Нет зарегистрированных пользователей")
        return

    monitor_logger.info(f"👥 Найдено пользователей: {len(users)}")

    for user in users:
        await monitor_single_user(user)
        await asyncio.sleep(2)

    monitor_logger.info("✅ Проверка подписок завершена")