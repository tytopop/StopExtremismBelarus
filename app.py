#!/usr/bin/env python3
"""
Flask веб-сервер для регистрации пользователей через Telethon
"""
import asyncio
from flask import Flask
from app.routes import bp
from db.database import init_db
from utils.logger import main_logger
import os
from dotenv import load_dotenv

load_dotenv()

# ВАЖНО: указываем правильный путь к templates
app = Flask(__name__, template_folder='app/templates')
app.register_blueprint(bp)

if __name__ == '__main__':
    # Инициализация БД при старте
    asyncio.run(init_db())
    main_logger.info("🚀 Flask сервер запущен")
    
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=False
    )
