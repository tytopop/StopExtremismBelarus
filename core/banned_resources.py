import asyncio
import os
from utils.logger import monitor_logger

banned_cache: set[str] = set()
CACHE_FILE = "downloads/resources.txt"

async def update_banned_cache():
    """Обновляет кэш - ВСЕГДА парсит с сайта заново."""
    global banned_cache
    try:
        monitor_logger.info("🔄 Запуск парсинга с сайта mininform.gov.by...")
        from core.parser import get_banned_resources
        
        # ВСЕГДА парсим заново
        new_resources = await get_banned_resources()
        banned_cache = {r.lower().strip() for r in new_resources if r}
        
        # Сохраняем в файл
        if banned_cache:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                for r in sorted(banned_cache):
                    f.write(r + '\n')
            monitor_logger.info(f"✅ Обновлён кэш: {len(banned_cache)} ресурсов")
            monitor_logger.info(f"💾 Сохранено в {CACHE_FILE}")
        else:
            monitor_logger.warning("⚠️ Парсер не нашёл ресурсов!")
            
    except Exception as e:
        monitor_logger.error(f"❌ Ошибка обновления кэша: {e}")
        import traceback
        traceback.print_exc()

def get_banned_set() -> set:
    """Возвращает кэш запрещённых ресурсов (синхронно)."""
    global banned_cache

    # Если кэш пустой - загружаем из файла
    if not banned_cache and os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            banned_cache = {line.strip().lower() for line in f if line.strip()}
        print(f"✅ Загружено из кэша: {len(banned_cache)} ресурсов")

    return banned_cache