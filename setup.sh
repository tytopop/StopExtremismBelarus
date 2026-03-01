#!/bin/bash
# 🚀 Скрипт быстрой установки StopExtremism
set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  🛡  УСТАНОВКА STOPEXTREMISM                              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден! Установите Python 3.10+"
    exit 1
fi
echo "✅ Python найден: $(python3 --version)"
echo ""

# Виртуальное окружение
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [[ ! -d "venv" ]]; then
        echo "📦 Создаю виртуальное окружение..."
        python3 -m venv venv
    fi
    echo "🔄 Активирую venv..."
    source venv/bin/activate
    echo "✅ venv активирован"
else
    echo "✅ venv уже активирован"
fi
echo ""

# Установка зависимостей
echo "📦 Установка зависимостей..."
pip install -q -r requirements.txt
echo "✅ Зависимости установлены"
echo ""

# Создание .env если нет
if [[ ! -f ".env" ]]; then
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  ⚙️  НАСТРОЙКА КОНФИГУРАЦИИ                               ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Для работы бота нужны API-ключи Telegram."
    echo ""
    echo "📌 BOT_TOKEN — получи у @BotFather в Telegram"
    echo "📌 API_ID и API_HASH — получи на https://my.telegram.org"
    echo ""

    read -p "🔑 Введите BOT_TOKEN: " BOT_TOKEN
    read -p "🔑 Введите API_ID: " API_ID
    read -p "🔑 Введите API_HASH: " API_HASH

    # Генерация SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

    cat > .env << ENVEOF
# Telegram Bot
BOT_TOKEN=${BOT_TOKEN}

# Telegram API
API_ID=${API_ID}
API_HASH=${API_HASH}

# Flask
SECRET_KEY=${SECRET_KEY}
FLASK_PORT=5000

# Monitoring (interval in seconds)
CHECK_INTERVAL=600
ENVEOF

    echo ""
    echo "✅ Файл .env создан"
else
    echo "✅ Файл .env уже существует"
fi
echo ""

# Создание директорий
echo "📁 Создание рабочих директорий..."
mkdir -p logs downloads
echo "✅ Директории созданы"
echo ""

# Инициализация БД
echo "🗄️  Инициализация базы данных..."
python3 << 'PYEOF'
import asyncio
from db.database import init_db
async def setup():
    await init_db()
    print("✅ База данных создана")
asyncio.run(setup())
PYEOF
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ✅ УСТАНОВКА ЗАВЕРШЕНА!                                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 Запуск проекта (откройте 3 терминала):"
echo ""
echo "  Терминал 1 — Telegram-бот:"
echo "    cd $(pwd) && source venv/bin/activate"
echo "    python3 bot.py"
echo ""
echo "  Терминал 2 — Worker мониторинга:"
echo "    cd $(pwd) && source venv/bin/activate"
echo "    python3 worker.py"
echo ""
echo "  Терминал 3 — Flask веб-панель:"
echo "    cd $(pwd) && source venv/bin/activate"
echo "    python3 app.py"
echo ""
echo "  Затем откройте: http://localhost:5000"
echo ""
echo "📝 Логи:"
echo "  logs/main.log     — Flask сервер"
echo "  logs/monitor.log  — Worker мониторинга"
echo ""
echo "💡 Совет: используйте systemd для автозапуска (см. README)"
echo ""
echo "✅ Готово! Удачи! 🛡"