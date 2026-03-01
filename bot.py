#!/usr/bin/env python3
"""
Telegram бот для управления и мониторинга системы StopExtremism
"""
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes
)
from db.database import get_all_users
from core.banned_resources import get_banned_set
from utils.logger import main_logger
import aiofiles
import psutil

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

# Глобальные переменные для статуса
LAST_CHECK_TIME = None
LAST_UPDATE_TIME = None
WORKER_STATUS = "Неизвестно"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - полная диагностика системы"""
    user_id = update.effective_user.id
    
    # Проверяем регистрацию
    users = await get_all_users()
    user_registered = any(u['user_id'] == user_id for u in users)
    
    # Диагностика системы
    diagnostics = await run_diagnostics()
    
    # Формируем сообщение
    message = f"""
🤖 <b>StopExtremism Bot</b>

👤 <b>Ваш статус:</b>
{"✅ Зарегистрирован" if user_registered else "❌ Не зарегистрирован"}

📊 <b>Статус системы:</b>

<b>🗄️ База запрещённых ресурсов:</b>
{diagnostics['resources_status']}
📦 Всего ресурсов: <b>{diagnostics['resources_count']}</b>
📅 Последнее обновление: <b>{diagnostics['last_update']}</b>

<b>🔍 Мониторинг подписок:</b>
{diagnostics['worker_status']}
⏱️ Последняя проверка: <b>{diagnostics['last_check']}</b>
👥 Пользователей в системе: <b>{diagnostics['users_count']}</b>

<b>💾 Система:</b>
{diagnostics['db_status']}
{diagnostics['parser_status']}

<b>📝 Доступные команды:</b>
/start - Статус системы
/check - Проверить подписки сейчас
/stats - Подробная статистика
/help - Помощь
"""
    
    # Кнопки
    keyboard = []
    
    if user_registered:
        keyboard.append([
            InlineKeyboardButton("🔍 Проверить сейчас", callback_data="check_now"),
            InlineKeyboardButton("📊 Статистика", callback_data="show_stats")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("📝 Зарегистрироваться", url=f"http://localhost:5000")
        ])
    
    keyboard.append([
        InlineKeyboardButton("❓ Помощь", callback_data="show_help"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="show_settings")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message, 
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def run_diagnostics():
    """Запускает полную диагностику системы"""
    diag = {}
    
    # 1. Проверка базы запрещённых ресурсов
    try:
        resources = get_banned_set()
        diag['resources_count'] = len(resources)
        diag['resources_status'] = "✅ Загружена"
        
        # Проверяем файл
        resources_file = "downloads/resources.txt"
        if os.path.exists(resources_file):
            file_time = datetime.fromtimestamp(os.path.getmtime(resources_file))
            diag['last_update'] = file_time.strftime("%d.%m.%Y %H:%M")
            
            # Проверяем актуальность (больше 24 часов = старая)
            age_hours = (datetime.now() - file_time).total_seconds() / 3600
            if age_hours > 24:
                diag['resources_status'] = f"⚠️ Устаревшая ({int(age_hours)}ч назад)"
        else:
            diag['last_update'] = "Никогда"
            diag['resources_status'] = "❌ Файл не найден"
    except Exception as e:
        diag['resources_count'] = 0
        diag['resources_status'] = "❌ Ошибка загрузки"
        diag['last_update'] = "Н/Д"
    
    # 2. Проверка worker
    try:
        # Проверяем логи
        log_file = "logs/monitor.log"
        if os.path.exists(log_file):
            async with aiofiles.open(log_file, 'r') as f:
                lines = await f.readlines()
                # Ищем последнюю проверку
                for line in reversed(lines[-100:]):
                    if "Начало проверки подписок" in line:
                        time_str = line.split()[0] + " " + line.split()[1]
                        check_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S,%f")
                        diag['last_check'] = check_time.strftime("%d.%m.%Y %H:%M")
                        
                        # Проверяем свежесть
                        age_min = (datetime.now() - check_time).total_seconds() / 60
                        if age_min < 15:
                            diag['worker_status'] = "✅ Работает"
                        else:
                            diag['worker_status'] = f"⚠️ Не проверял {int(age_min)}мин"
                        break
                else:
                    diag['last_check'] = "Не найдено"
                    diag['worker_status'] = "❌ Не работает"
        else:
            diag['last_check'] = "Нет логов"
            diag['worker_status'] = "❌ Логов нет"
    except Exception:
        diag['last_check'] = "Ошибка"
        diag['worker_status'] = "❌ Ошибка"
    
    # 3. Количество пользователей
    try:
        users = await get_all_users()
        diag['users_count'] = len(users)
    except:
        diag['users_count'] = 0
    
    # 4. Проверка БД
    if os.path.exists("db/users.db"):
        db_size = os.path.getsize("db/users.db") / 1024  # KB
        diag['db_status'] = f"✅ БД: {db_size:.1f} KB"
    else:
        diag['db_status'] = "❌ БД не найдена"
    
    # 5. Проверка парсера (LibreOffice)
    try:
        import subprocess
        result = subprocess.run(['which', 'soffice'], capture_output=True)
        if result.returncode == 0:
            diag['parser_status'] = "✅ Парсер готов"
        else:
            diag['parser_status'] = "⚠️ LibreOffice не найден"
    except:
        diag['parser_status'] = "❌ Парсер недоступен"
    
    return diag


async def check_now_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: Проверить подписки сейчас"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Запускаем проверку
    await query.edit_message_text("🔍 Запускаю проверку подписок...\n⏳ Это может занять до 30 секунд")
    
    try:
        from core.subscription_monitor import monitor_single_user
        from db.database import get_all_users
        
        users = await get_all_users()
        user_data = next((u for u in users if u['user_id'] == user_id), None)
        
        if user_data:
            await monitor_single_user(user_data)
            await query.edit_message_text(
                "✅ Проверка завершена!\n\n"
                "Если найдены запрещённые подписки, вы получите отдельное уведомление."
            )
        else:
            await query.edit_message_text("❌ Вы не зарегистрированы в системе")
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка при проверке: {str(e)}")


async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: Показать статистику"""
    query = update.callback_query
    await query.answer()
    
    diagnostics = await run_diagnostics()
    
    # Дополнительная статистика
    resources = get_banned_set()
    
    # Группируем по типам
    usernames = [r for r in resources if not r.startswith('id_') and len(r) < 20]
    ids = [r for r in resources if r.startswith('id_')]
    names = [r for r in resources if r not in usernames and r not in ids]
    
    message = f"""
📊 <b>Подробная статистика</b>

<b>🗄️ База запрещённых:</b>
📦 Всего ресурсов: {len(resources)}
  • @username: {len(usernames)}
  • ID каналов: {len(ids)}
  • Названия: {len(names)}

<b>📅 Актуальность:</b>
Последнее обновление: {diagnostics['last_update']}
Последняя проверка: {diagnostics['last_check']}

<b>👥 Пользователи:</b>
Зарегистрировано: {diagnostics['users_count']}

<b>💾 Система:</b>
{diagnostics['db_status']}
{diagnostics['parser_status']}
{diagnostics['worker_status']}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)


async def show_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: Помощь"""
    query = update.callback_query
    await query.answer()
    
    message = """
❓ <b>Справка StopExtremism Bot</b>

<b>Что делает бот?</b>
Автоматически проверяет ваши Telegram-подписки на наличие каналов из списка экстремистских материалов РБ и уведомляет вас.

<b>Как работает?</b>
1. Парсер обновляет список 2 раза в день (00:05 и 12:05)
2. Ваши подписки проверяются каждые 10 минут
3. При обнаружении запрещённого канала приходит уведомление

<b>Команды:</b>
/start - Статус системы
/check - Проверить подписки сейчас
/stats - Подробная статистика
/help - Эта справка

<b>⚠️ Важно:</b>
• Бот НЕ может отписать вас автоматически
• Вы должны сами покинуть запрещённый канал
• После отписки бот подтвердит что всё в порядке

<b>🔒 Безопасность:</b>
• Ваши данные зашифрованы
• Бот только читает список подписок
• Не может отправлять сообщения от вашего имени
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)


async def show_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: Настройки"""
    query = update.callback_query
    await query.answer()
    
    message = """
⚙️ <b>Настройки</b>

<b>Текущая конфигурация:</b>
📊 Проверка подписок: каждые 10 минут
📅 Обновление базы: 00:05 и 12:05 ежедневно

<b>Доступные действия:</b>
"""
    
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить сейчас", callback_data="check_now")],
        [InlineKeyboardButton("🔄 Обновить базу", callback_data="update_db")],
        [InlineKeyboardButton("📋 Список подписок", callback_data="show_subscriptions")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)


async def update_db_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: Принудительное обновление базы"""
    query = update.callback_query
    await query.answer("Запускаю обновление базы...")
    
    await query.edit_message_text("🔄 Обновление базы запрещённых ресурсов...\n⏳ Это может занять 1-2 минуты")
    
    try:
        from core.banned_resources import update_banned_cache
        await update_banned_cache()
        
        resources = get_banned_set()
        
        await query.edit_message_text(
            f"✅ База успешно обновлена!\n\n"
            f"📦 Всего ресурсов: <b>{len(resources)}</b>\n"
            f"📅 Обновлено: <b>{datetime.now().strftime('%d.%m.%Y %H:%M')}</b>",
            parse_mode='HTML'
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка обновления: {str(e)}")


async def show_subscriptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: Показать подписки пользователя"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    await query.edit_message_text("🔍 Загружаю список ваших подписок...")
    
    try:
        from db.database import get_all_users
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from utils.crypto import decrypt_session
        
        users = await get_all_users()
        user_data = next((u for u in users if u['user_id'] == user_id), None)
        
        if not user_data:
            await query.edit_message_text("❌ Вы не зарегистрированы в системе")
            return
        
        session_data = decrypt_session(user_data['session_data'])
        client = TelegramClient(StringSession(session_data), user_data['api_id'], user_data['api_hash'])
        
        await client.connect()
        
        channels = []
        async for dialog in client.iter_dialogs():
            if (dialog.is_channel or dialog.is_group) and len(channels) < 50:
                entity = dialog.entity
                username = getattr(entity, 'username', None)
                title = getattr(entity, 'title', 'Без названия')
                channels.append(f"• {title}" + (f" (@{username})" if username else ""))
        
        await client.disconnect()
        
        message = f"📱 <b>Ваши подписки ({len(channels)}):</b>\n\n"
        message += "\n".join(channels[:30])
        if len(channels) > 30:
            message += f"\n\n... и ещё {len(channels) - 30}"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")


async def recheck_after_unsubscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: Повторная проверка после отписки"""
    query = update.callback_query
    await query.answer("Проверяю...")
    
    # Извлекаем user_id из callback_data
    user_id = int(query.data.split('_')[1])
    
    # Проверяем что это действительно тот пользователь
    if query.from_user.id != user_id:
        await query.answer("Ошибка: это не ваша кнопка", show_alert=True)
        return
    
    await query.edit_message_text("🔍 Проверяю ваши подписки...\n⏳ Подождите 10-15 секунд")
    
    try:
        from core.subscription_monitor import monitor_single_user
        from db.database import get_all_users
        
        users = await get_all_users()
        user_data = next((u for u in users if u['user_id'] == user_id), None)
        
        if user_data:
            # Запускаем проверку
            await monitor_single_user(user_data)
            
            await query.edit_message_text(
                "✅ <b>Проверка завершена!</b>\n\n"
                "Если вы отписались от всех запрещённых каналов, "
                "вы получите подтверждающее сообщение.\n\n"
                "Если запрещённые подписки ещё остались, "
                "придёт новое уведомление.",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("❌ Ошибка: пользователь не найден в системе")
            
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка при проверке: {str(e)}")


async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: Вернуться к /start"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Проверяем регистрацию
    users = await get_all_users()
    user_registered = any(u['user_id'] == user_id for u in users)
    
    # Диагностика системы
    diagnostics = await run_diagnostics()
    
    # Формируем сообщение (КОПИЯ из start_command)
    message = f"""
🤖 <b>StopExtremism Bot</b>

👤 <b>Ваш статус:</b>
{"✅ Зарегистрирован" if user_registered else "❌ Не зарегистрирован"}

📊 <b>Статус системы:</b>

<b>🗄️ База запрещённых ресурсов:</b>
{diagnostics['resources_status']}
📦 Всего ресурсов: <b>{diagnostics['resources_count']}</b>
📅 Последнее обновление: <b>{diagnostics['last_update']}</b>

<b>🔍 Мониторинг подписок:</b>
{diagnostics['worker_status']}
⏱️ Последняя проверка: <b>{diagnostics['last_check']}</b>
👥 Пользователей в системе: <b>{diagnostics['users_count']}</b>

<b>💾 Система:</b>
{diagnostics['db_status']}
{diagnostics['parser_status']}

<b>📝 Доступные команды:</b>
/start - Статус системы
/check - Проверить подписки сейчас
/stats - Подробная статистика
/help - Помощь
"""
    
    # Кнопки
    keyboard = []
    
    if user_registered:
        keyboard.append([
            InlineKeyboardButton("🔍 Проверить сейчас", callback_data="check_now"),
            InlineKeyboardButton("📊 Статистика", callback_data="show_stats")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("📝 Зарегистрироваться", url=f"http://localhost:5000")
        ])
    
    keyboard.append([
        InlineKeyboardButton("❓ Помощь", callback_data="show_help"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="show_settings")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message, 
        parse_mode='HTML',
        reply_markup=reply_markup
    )


def main():
    """Запуск бота"""
    main_logger.info("🤖 Запуск Telegram бота...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start_command))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(check_now_callback, pattern="^check_now$"))
    application.add_handler(CallbackQueryHandler(show_stats_callback, pattern="^show_stats$"))
    application.add_handler(CallbackQueryHandler(show_help_callback, pattern="^show_help$"))
    application.add_handler(CallbackQueryHandler(show_settings_callback, pattern="^show_settings$"))
    application.add_handler(CallbackQueryHandler(update_db_callback, pattern="^update_db$"))
    application.add_handler(CallbackQueryHandler(show_subscriptions_callback, pattern="^show_subscriptions$"))
    application.add_handler(CallbackQueryHandler(recheck_after_unsubscribe_callback, pattern="^recheck_"))
    application.add_handler(CallbackQueryHandler(back_to_start_callback, pattern="^back_to_start$"))
    
    # Запуск
    main_logger.info("✅ Бот запущен и готов к работе")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()