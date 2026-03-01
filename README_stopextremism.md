# 🛡 StopExtremism Bot

[English](#english) | [Русский](#русский)

---

<a name="english"></a>

## 🇬🇧 English

### About

Telegram bot that monitors users' channel subscriptions against the official Belarus banned resources registry. Automatically parses the Ministry of Information database (4,300+ entries), checks subscriptions on a schedule, and sends instant notifications if a match is found.

### Features

- 🔍 **Subscription Monitoring** — automatic periodic checks of user's Telegram subscriptions
- 📋 **Registry Parsing** — auto-download and parsing of the banned resources list from mininform.gov.by
- 🔔 **Instant Notifications** — alerts via Telegram with inline buttons when a banned channel is detected
- 📊 **Web Dashboard** — Flask-based statistics panel with system health monitoring
- ⏰ **Scheduler** — configurable check intervals (default: every 10 minutes)
- 🔄 **Auto-Update** — registry refreshes twice daily (00:05 and 12:05)
- ✅ **Unsubscribe Confirmation** — follow-up notification after user unsubscribes

### Architecture

```
StopExtremism/
├── bot.py                  # Telegram bot (inline keyboards, diagnostics)
├── app.py                  # Flask web interface
├── worker.py               # Background scheduler
├── core/
│   ├── subscription_monitor.py  # Subscription checking logic
│   └── banned_resources.py      # Registry parser & cache
├── db/
│   └── database.py         # SQLite database layer
├── downloads/
│   └── resources.txt       # Cached banned resources list
└── logs/
    └── monitor.log         # Application logs
```

### Tech Stack

- **Python 3.10+**
- **Telethon** — Telegram client API for subscription access
- **Flask** — web dashboard
- **SQLite** — user database
- **BeautifulSoup4** — HTML parsing of government registry
- **APScheduler** — task scheduling
- **systemd** — process management & auto-restart

### Installation

```bash
# Clone the repository
git clone https://github.com/tytopop/StopExtremism.git
cd StopExtremism

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials:
#   BOT_TOKEN - Telegram bot token from @BotFather
#   API_ID    - Telegram API ID from my.telegram.org
#   API_HASH  - Telegram API Hash from my.telegram.org

# Run
python3 bot.py     # Telegram bot
python3 worker.py  # Background monitoring
python3 app.py     # Web dashboard
```

### Screenshots

<!-- Add screenshots here -->
<!-- ![Bot Start](screenshots/bot_start.png) -->
<!-- ![Dashboard](screenshots/dashboard.png) -->

### License

MIT

---

<a name="русский"></a>

## 🇷🇺 Русский

### О проекте

Telegram-бот для мониторинга подписок пользователей на каналы из реестра запрещённых ресурсов Республики Беларусь. Автоматически парсит базу данных Мининформа (4300+ записей), проверяет подписки по расписанию и мгновенно уведомляет при обнаружении совпадений.

### Возможности

- 🔍 **Мониторинг подписок** — автоматические периодические проверки Telegram-подписок пользователя
- 📋 **Парсинг реестра** — авто-загрузка и парсинг списка запрещённых ресурсов с mininform.gov.by
- 🔔 **Мгновенные уведомления** — оповещения в Telegram с inline-кнопками при обнаружении запрещённого канала
- 📊 **Веб-панель** — статистика и мониторинг здоровья системы на Flask
- ⏰ **Планировщик** — настраиваемый интервал проверок (по умолчанию: каждые 10 минут)
- 🔄 **Авто-обновление** — реестр обновляется дважды в день (00:05 и 12:05)
- ✅ **Подтверждение отписки** — повторное уведомление после отписки пользователя

### Архитектура

```
StopExtremism/
├── bot.py                  # Telegram-бот (inline-клавиатуры, диагностика)
├── app.py                  # Flask веб-интерфейс
├── worker.py               # Фоновый планировщик
├── core/
│   ├── subscription_monitor.py  # Логика проверки подписок
│   └── banned_resources.py      # Парсер реестра и кэш
├── db/
│   └── database.py         # Слой базы данных SQLite
├── downloads/
│   └── resources.txt       # Кэш списка запрещённых ресурсов
└── logs/
    └── monitor.log         # Логи приложения
```

### Стек технологий

- **Python 3.10+**
- **Telethon** — клиентский API Telegram для доступа к подпискам
- **Flask** — веб-панель
- **SQLite** — база данных пользователей
- **BeautifulSoup4** — HTML-парсинг государственного реестра
- **APScheduler** — планирование задач
- **systemd** — управление процессами и авто-перезапуск

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/tytopop/StopExtremism.git
cd StopExtremism

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Настроить окружение
cp .env.example .env
# Отредактируй .env:
#   BOT_TOKEN - токен бота от @BotFather
#   API_ID    - Telegram API ID с my.telegram.org
#   API_HASH  - Telegram API Hash с my.telegram.org

# Запуск
python3 bot.py     # Telegram-бот
python3 worker.py  # Фоновый мониторинг
python3 app.py     # Веб-панель
```

### Скриншоты

<!-- Добавь скриншоты сюда -->
<!-- ![Старт бота](screenshots/bot_start.png) -->
<!-- ![Панель](screenshots/dashboard.png) -->

### Лицензия

MIT
