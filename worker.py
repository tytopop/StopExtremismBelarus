#!/usr/bin/env python3
"""
Worker процесс для фонового мониторинга подписок
Запускается отдельно от Flask
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.banned_resources import update_banned_cache
from core.subscription_monitor import monitor_all_users_once
from db.database import init_db
from utils.logger import monitor_logger
import signal
import sys

scheduler = AsyncIOScheduler()
shutdown_event = asyncio.Event()

def handle_shutdown(signum, frame):
    """Обработка Ctrl+C и kill"""
    monitor_logger.info("📛 Получен сигнал остановки")
    shutdown_event.set()

async def main():
    # Инициализация БД
    await init_db()
    monitor_logger.info("✅ База данных инициализирована")
    
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Первый запуск - обновляем список сразу
    monitor_logger.info("🔄 Первоначальное обновление списка запрещённых ресурсов...")
    await update_banned_cache()

    # Планировщик: обновление списка в 00:05 и 12:05 каждый день
    scheduler.add_job(
        update_banned_cache,
        trigger=CronTrigger(hour="0,12", minute=5),
        id='update_banned_list',
        name='Обновление списка 2 раза в сутки',
        replace_existing=True
    )

    # Планировщик: проверка подписок каждые 10 минут
    scheduler.add_job(
        monitor_all_users_once,
        'interval',
        minutes=10,
        id='monitor_subscriptions',
        name='Периодическая проверка подписок',
        replace_existing=True
    )

    scheduler.start()
    monitor_logger.info("🚀 Планировщик запущен:")
    monitor_logger.info("   → Обновление списка: 00:05 и 12:05 ежедневно")
    monitor_logger.info("   → Проверка подписок: каждые 10 минут")

    # Держим процесс живым до получения сигнала
    try:
        await shutdown_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        monitor_logger.info("🛑 Остановка планировщика...")
        scheduler.shutdown()
        monitor_logger.info("👋 Worker завершён")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Пока!")
