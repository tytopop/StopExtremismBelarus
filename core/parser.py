import aiohttp
import re
import os
import subprocess
from urllib.parse import urljoin
from bs4 import BeautifulSoup

URL = "http://mininform.gov.by/documents/respublikanskiy-spisok-ekstremistskikh-materialov/"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DOWNLOAD_DIR, "resources.txt")

async def fetch(url):
    """Скачивание файла или страницы."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.read()

def convert_doc_to_docx(doc_path):
    """Конвертация .doc → .docx через LibreOffice."""
    docx_path = os.path.splitext(doc_path)[0] + ".docx"
    if os.path.exists(docx_path):
        print(f"ℹ️  .docx уже существует: {docx_path}")
        return docx_path

    try:
        print(f"🔄 Конвертация {doc_path}...")
        subprocess.run([
            "soffice", "--headless", "--convert-to", "docx", doc_path, "--outdir", DOWNLOAD_DIR
        ], check=True, capture_output=True, timeout=60)

        if os.path.exists(docx_path):
            print(f"✅ Конвертирован: {docx_path}")
            return docx_path
    except Exception as e:
        print(f"❌ Ошибка конвертации: {e}")
    return None

def parse_docx_fast(docx_path):
    """БЫСТРЫЙ парсинг через XML с ПОЛНОЙ склейкой."""
    try:
        print(f"📖 Быстрый парсинг {os.path.basename(docx_path)}...")

        temp_xml = os.path.join(DOWNLOAD_DIR, "temp.xml")
        subprocess.run([
            "unzip", "-p", docx_path, "word/document.xml"
        ], stdout=open(temp_xml, 'w'), check=True)

        with open(temp_xml, 'r', encoding='utf-8') as f:
            xml_text = f.read()

        # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: удаляем ВСЕ теги между <w:t>текст</w:t>
        # nexta_</w:t></w:r><w:r><w:rPr>...<w:t>live → nexta_live
        xml_text = re.sub(r'</w:t>.*?<w:t[^>]*>', '', xml_text)
        
        # Извлекаем текст
        text_content = re.findall(r'>([^<]+)<', xml_text)
        full_text = " ".join(text_content)

        os.remove(temp_xml)
        print(f"✅ Извлечено {len(full_text)} символов")
        return full_text

    except Exception as e:
        print(f"❌ Ошибка парсинга XML: {e}")
        return ""

def extract_telegram_resources(text: str) -> set:
    """Извлекает Telegram-ресурсы."""
    print("🔍 Поиск Telegram-ресурсов...")
    resources = set()

    # 1. ПРЯМЫЕ ССЫЛКИ t.me
    links = re.findall(r'https?://t\.me/([a-zA-Z0-9_]+)', text, re.IGNORECASE)
    print(f"   🔗 Прямых ссылок: {len(set(links))}")
    resources.update([l.lower() for l in links])

    # 2. @USERNAME рядом с Telegram
    telegram_sections = re.findall(r'.{0,100}[Tt]elegram.{0,100}', text)
    for section in telegram_sections:
        users = re.findall(r'@([a-zA-Z0-9_]{5,})', section)
        resources.update([u.lower() for u in users])
    
    print(f"   @ Usernames: {len(set([r for r in resources if not r.startswith('id_')]))}")

    # 3. ID с контекстом
    id_matches = re.findall(r'(?:идентификатор|identificator|ID)[^\d]{0,50}(\d{10,})', text, re.IGNORECASE)
    print(f"   🆔 ID: {len(set(id_matches))}")
    resources.update([f"id_{i}" for i in id_matches])

    # 4. НАЗВАНИЯ КАНАЛОВ в кавычках
    lines_with_telegram = [line for line in text.split('\n') if 'elegram' in line.lower()]
    for line in lines_with_telegram:
        names = re.findall(r'["«]([А-ЯЁA-Z][^"»]{3,40})["»]', line)
        for name in names:
            if not re.search(r'[\d._/\\]', name):
                clean = re.sub(r'[^\wА-Яа-яЁё\s]', '', name).strip().lower().replace(' ', '_')
                if len(clean) >= 4 and clean not in ['telegram', 'канал', 'группа', 'чат', 'бот']:
                    resources.add(clean)

    # Финальная фильтрация
    resources = {
        r.lower().strip() 
        for r in resources 
        if r and len(r) >= 4 
        and not re.match(r'^\d+$', r)
        and not r.endswith(('_mp_3', '_mp_4', '_flv', '_wmv'))
    }

    print(f"✅ Найдено уникальных ресурсов: {len(resources)}")
    return resources

async def download_and_parse():
    """Основной процесс."""
    print("🌐 Загрузка страницы...")
    html = await fetch(URL)
    soup = BeautifulSoup(html, 'html.parser')

    doc_link = None
    for a in soup.find_all('a', href=True):
        if a['href'].endswith('.doc'):
            doc_link = urljoin(URL, a['href'])
            break

    if not doc_link:
        print("❌ Не найдена ссылка на .doc")
        return

    print(f"⬇️  Скачивание {doc_link}...")
    doc_data = await fetch(doc_link)
    
    doc_filename = os.path.basename(doc_link)
    doc_path = os.path.join(DOWNLOAD_DIR, doc_filename)
    
    with open(doc_path, 'wb') as f:
        f.write(doc_data)
    
    print(f"✅ Сохранён: {doc_path}")

    docx_path = convert_doc_to_docx(doc_path)
    if not docx_path:
        return

    text = parse_docx_fast(docx_path)
    if not text:
        print("❌ Не удалось извлечь текст")
        return

    resources = extract_telegram_resources(text)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sorted(resources)))

    print(f"💾 Сохранено в {OUTPUT_FILE}")
    print(f"📊 Всего ресурсов: {len(resources)}")


async def get_banned_resources():
    """Скачивает и парсит все запрещённые ресурсы с сайта."""
    resources = set()
    print(f"🔍 Обновляем список запрещённых ресурсов...")
    
    try:
        html = await fetch(URL)
        soup = BeautifulSoup(html, 'html.parser')
        
        links = [
            urljoin(URL, a['href']) for a in soup.find_all('a', href=True)
            if any(a['href'].endswith(ext) for ext in ('.doc', '.docx', '.pdf'))
        ]
        
        print(f"📄 Документов: {len(links)}")
        
        for link in links:
            filename = os.path.join(DOWNLOAD_DIR, os.path.basename(link))
            
            # Скачивание
            if not os.path.exists(filename):
                content = await fetch(link)
                with open(filename, "wb") as f:
                    f.write(content)
                print(f"📄 Скачано: {filename}")
            
            # Парсинг
            if link.endswith(".doc"):
                docx_path = convert_doc_to_docx(filename)
                if docx_path:
                    text = parse_docx_fast(docx_path)
                    if text:
                        extracted = extract_telegram_resources(text)
                        resources.update(extracted)
            elif link.endswith(".docx"):
                text = parse_docx_fast(filename)
                if text:
                    extracted = extract_telegram_resources(text)
                    resources.update(extracted)
        
        resources = {r.lower().strip() for r in resources if r}
        print(f"\n✅ Всего уникальных ресурсов: {len(resources)}")
        
        if resources:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                for r in sorted(resources):
                    f.write(r + "\n")
            print(f"💾 Сохранено в: {OUTPUT_FILE}")
        
        return resources
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return set()
