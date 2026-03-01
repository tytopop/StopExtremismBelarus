from flask import Blueprint, request, render_template, redirect, url_for
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import asyncio
import os
import traceback
from dotenv import load_dotenv
from utils.crypto import encrypt_session
from db.database import DB_PATH
from utils.logger import main_logger
from telegram import Bot

load_dotenv()
bp = Blueprint('main', __name__)

bot = Bot(token=os.getenv("BOT_TOKEN"))

def get_db_connection():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

async def send_user_message(user_id: int, text: str):
    """Асинхронная отправка сообщения через бота"""
    try:
        await bot.send_message(chat_id=user_id, text=text)
    except Exception as e:
        main_logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")

def run_async(coro):
    """Запуск асинхронной функции в новом event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.close()
        except:
            pass

# ================== ROUTES ==================

@bp.route('/')
def index():
    return render_template('index.html', bot_name=os.getenv("TELEGRAM_BOT_NAME", "AlertBot"))

@bp.route('/setup', methods=['POST'])
def setup():
    try:
        user_id = int(request.form['user_id'])
        api_id = int(request.form['api_id'])
        api_hash = request.form['api_hash']
        phone = request.form['phone']
    except Exception as e:
        main_logger.error(f"Ошибка валидации: {e}")
        return "<h2>❌ Проверьте введённые данные — API ID должен быть числом.</h2>"

    async def do_setup():
        # ВАЖНО: Создаём клиент ВНУТРИ async функции
        client = TelegramClient(StringSession(), api_id, api_hash)
        
        await client.connect()
        
        if not await client.is_user_authorized():
            sent_code = await client.send_code_request(phone)
            phone_code_hash = sent_code.phone_code_hash
            temp_session = client.session.save()
            await client.disconnect()
            return render_template(
                'verify.html',
                user_id=user_id,
                api_id=api_id,
                api_hash=api_hash,
                phone=phone,
                phone_code_hash=phone_code_hash,
                temp_session=temp_session
            )

        # Уже авторизован
        session_str = client.session.save()
        encrypted_session = encrypt_session(session_str)
        await client.disconnect()

        conn = get_db_connection()
        conn.execute(
            "INSERT OR REPLACE INTO users (user_id, api_id, api_hash, session_data, phone) VALUES (?, ?, ?, ?, ?)",
            (user_id, api_id, api_hash, encrypted_session, phone)
        )
        conn.commit()
        conn.close()

        await send_user_message(user_id, "✅ Ваш аккаунт подключён к системе мониторинга!")
        return redirect(url_for('main.success_page'))

    try:
        return run_async(do_setup())
    except Exception as e:
        main_logger.error(f"Ошибка в /setup: {e}")
        traceback.print_exc()
        return f"<h2>❌ Ошибка: {str(e)}</h2>"

@bp.route('/verify', methods=['POST'])
def verify():
    required_fields = ['user_id', 'api_id', 'api_hash', 'phone', 'phone_code_hash', 'temp_session']
    missing = [field for field in required_fields if not request.form.get(field)]
    if missing:
        return f"<h2>❌ Отсутствуют поля: {', '.join(missing)}</h2><br><a href='/'>← Назад</a>"

    try:
        user_id = int(request.form['user_id'])
        api_id = int(request.form['api_id'])
        api_hash = request.form['api_hash']
        phone = request.form['phone']
        code = request.form.get('code')
        phone_code_hash = request.form['phone_code_hash']
        temp_session = request.form['temp_session']
        password = request.form.get('password')
    except Exception as e:
        traceback.print_exc()
        return f"<h2>❌ Ошибка парсинга: {str(e)}</h2><br><a href='/'>← Назад</a>"

    async def do_verify():
        # ВАЖНО: Создаём клиент ВНУТРИ async функции
        client = TelegramClient(StringSession(temp_session), api_id, api_hash)
        
        await client.connect()

        if password:
            await client.sign_in(password=password)
        else:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)

        session_str = client.session.save()
        encrypted_session = encrypt_session(session_str)
        await client.disconnect()

        conn = get_db_connection()
        conn.execute(
            "INSERT OR REPLACE INTO users (user_id, api_id, api_hash, session_data, phone) VALUES (?, ?, ?, ?, ?)",
            (user_id, api_id, api_hash, encrypted_session, phone)
        )
        conn.commit()
        conn.close()

        await send_user_message(user_id, "✅ Ваш аккаунт подключён к системе мониторинга!")
        return redirect(url_for('main.success_page'))

    try:
        return run_async(do_verify())
    except SessionPasswordNeededError:
        return render_template('password.html', user_id=user_id, api_id=api_id,
                               api_hash=api_hash, phone=phone, code=code or "",
                               phone_code_hash=phone_code_hash, temp_session=temp_session)
    except Exception as e:
        traceback.print_exc()
        return f"<h2>❌ Ошибка входа: {str(e)}</h2><br><a href='/'>← Назад</a>"

@bp.route('/success')
def success_page():
    return render_template('success.html')

@bp.route('/delete', methods=['GET', 'POST'])
def delete():
    if request.method == 'POST':
        user_id = int(request.form['user_id'])
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return "<h2>✅ Ваш аккаунт удалён из системы.</h2>"
    return render_template('delete.html')
