import io
import re
import json
import base64
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

import httpx
from config import YANDEX_API_KEY


CATEGORIES = {
    "food": "Еда", "transport": "Транспорт", "housing": "Жильё",
    "utilities": "Коммуналка", "health": "Здоровье", "education": "Обучение",
    "entertainment": "Развлечения", "clothing": "Одежда", "electronics": "Техника",
    "subscriptions": "Подписки", "services": "Услуги", "other": "Другое",
}

FOLDER_ID = "b1gac3anu4uqll2jsfh2"


def preprocess_image(image_bytes: bytes) -> list:
    """Несколько вариантов предобработки для лучшего OCR."""
    img = Image.open(io.BytesIO(image_bytes))
    variants = []

    # Вариант 1: яркий контраст
    v1 = img.convert("L")
    v1 = ImageEnhance.Contrast(v1).enhance(3.0)
    v1 = v1.filter(ImageFilter.SHARPEN)
    variants.append(v1)

    # Вариант 2: инверсия (тёмный фон → светлый)
    v2 = ImageOps.invert(img.convert("L"))
    v2 = ImageEnhance.Contrast(v2).enhance(3.0)
    v2 = v2.filter(ImageFilter.SHARPEN)
    variants.append(v2)

    # Вариант 3: бинаризация
    v3 = img.convert("L")
    v3 = v3.point(lambda x: 255 if x > 100 else 0, "1")
    variants.append(v3)

    # Вариант 4: увеличение + контраст
    try:
        v4 = img.convert("L")
        v4 = v4.resize((v4.width * 2, v4.height * 2), Image.LANCZOS)
        v4 = ImageEnhance.Contrast(v4).enhance(2.0)
        variants.append(v4)
    except Exception:
        pass

    return variants


def extract_text_tesseract(image_bytes: bytes) -> str:
    """Tesseract OCR с несколькими вариантами предобработки."""
    if not TESSERACT_AVAILABLE:
        return ""

    try:
        variants = preprocess_image(image_bytes)
        best_text = ""

        for variant in variants:
            try:
                text = pytesseract.image_to_string(
                    variant, lang="rus+eng", config="--oem 3 --psm 6"
                )
                if len(text.strip()) > len(best_text.strip()):
                    best_text = text
            except Exception:
                continue

        return best_text.strip()
    except Exception:
        return ""


async def yandex_ocr(image_bytes: bytes) -> str:
    """Yandex Cloud Vision API."""
    if not YANDEX_API_KEY:
        return ""

    b64 = base64.b64encode(image_bytes).decode()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText",
                headers={
                    "Authorization": f"Api-Key {YANDEX_API_KEY}",
                    "Content-Type": "application/json",
                    "x-folder-id": FOLDER_ID,
                },
                json={"language": "rus", "model": "page", "mimeType": "image/jpeg", "content": b64},
            )
            if resp.status_code == 200:
                data = resp.json()
                blocks = data.get("result", {}).get("textAnnotation", {}).get("blocks", [])
                lines = []
                for block in blocks:
                    for line in block.get("lines", []):
                        lines.append(line.get("text", ""))
                return "\n".join(lines)
    except Exception:
        pass

    return ""


def parse_expense(text: str) -> dict:
    """Парсит текст чека/скриншота в структурированные данные."""
    result = {
        "amount": None, "currency": "RUB", "date": None,
        "merchant": None, "category": "other", "items": [], "raw_text": text,
        "all_amounts": [],
    }

    # === ВСЕ СУММЫ ===
    all_numbers = re.findall(r"(\d+[\s]*\d*[.,]\d{2})", text)
    all_amounts = []
    for n in all_numbers:
        try:
            val = float(n.replace(" ", "").replace(",", "."))
            if val > 0 and val not in all_amounts:
                all_amounts.append(val)
        except ValueError:
            continue
    all_amounts.sort(reverse=True)
    result["all_amounts"] = all_amounts[:10]

    # === ИТОГО (приоритетная сумма) ===
    amount_patterns = [
        r"(?:ИТОГО|Итого|Всего|ВСЕГО|СУММА|К оплате|Оплата|Оплачено)[:\s]*([\d\s]+[.,]\d{2})",
        r"(?:total|Total)[:\s]*([\d\s]+[.,]\d{2})",
        r"([\d]+[.,]\d{2})\s*(?:₽|руб|RUB|рублей)",
    ]
    for pat in amount_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1).replace(" ", "").replace(",", "."))
                if val > 0:
                    result["amount"] = val
                    break
            except ValueError:
                continue

    if not result["amount"] and all_amounts:
        result["amount"] = all_amounts[0]

    # === ДАТА ===
    for pat, fmt in [
        (r"(\d{2}\.\d{2}\.\d{4})", "%d.%m.%Y"),
        (r"(\d{2}\.\d{2}\.\d{2})", "%d.%m.%y"),
    ]:
        m = re.search(pat, text)
        if m:
            try:
                result["date"] = datetime.strptime(m.group(1), fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

    # === КАТЕГОРИЯ ===
    cat_kw = {
        "food": ["продукт", "еда", "магазин", "пятёрочка", "пятерочка", "магнит", "лента", "ашан", "вкусно", "каштан", "перекрёсток", "выручка"],
        "transport": ["такси", "метро", "автобус", "транспорт", "яндекс.проезд", "каршеринг", "яндекс", "бензин", "АЗС", "заправк"],
        "utilities": ["квартплата", "жкх", "коммунал", "водоканал", "электричество", "газпром", "тепло"],
        "health": ["аптека", "врач", "больниц", "clinic", "мед", "анализ"],
        "entertainment": ["кино", "театр", "ресторан", "кафе", "бар", "доставка", "яндекс.еда", "самокат"],
        "clothing": ["одежд", "обувь", "zara", "h&m"],
        "electronics": ["электроник", "техник", "mvideo", "dns", "citilink"],
        "subscriptions": ["подписк", "spotify", "netflix", "ivi", "kinopoisk"],
    }
    tl = text.lower()
    for cat, kws in cat_kw.items():
        if any(kw in tl for kw in kws):
            result["category"] = cat
            break

    # === ТОВАРЫ ===
    for line in text.split("\n"):
        m = re.match(r"(.+?)\s+(\d+[.,]\d{2})\s*(?:₽|руб)?\s*$", line.strip())
        if m and m.group(2):
            try:
                price = float(m.group(2).replace(",", "."))
                name = m.group(1).strip()
                if price > 0 and len(name) > 1 and name.lower() not in ("итого", "всего", "сумма"):
                    result["items"].append({"name": name[:100], "price": price})
            except ValueError:
                continue

    return result


def extract_text_pdf(pdf_bytes: bytes) -> str:
    """Извлекает текст из PDF через pdfplumber."""
    if not PDF_AVAILABLE:
        return ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texts = []
            for page in pdf.pages[:10]:
                text = page.extract_text()
                if text:
                    texts.append(text)
            return "\n".join(texts).strip()
    except Exception:
        return ""


def analyze_pdf(pdf_bytes: bytes) -> dict:
    """Анализ PDF-файла (выписка, чек)."""
    text = extract_text_pdf(pdf_bytes)
    if not text or len(text.strip()) < 10:
        return {
            "amount": None, "currency": "RUB", "date": None,
            "merchant": None, "category": "other", "items": [],
            "raw_text": "Не удалось извлечь текст из PDF", "source": "pdf_failed",
        }
    result = parse_expense(text)
    result["source"] = "pdf"
    return result


async def analyze_photo(image_bytes: bytes) -> dict:
    """Полный пайплайн: фото → OCR → парсинг."""
    text = await yandex_ocr(image_bytes)
    source = "yandex_ocr"

    if not text or len(text.strip()) < 10:
        text = extract_text_tesseract(image_bytes)
        source = "tesseract"

    if not text or len(text.strip()) < 5:
        return {
            "amount": None, "currency": "RUB", "date": None,
            "merchant": None, "category": "other", "items": [],
            "raw_text": "Не удалось распознать текст", "source": "failed",
        }

    result = parse_expense(text)
    result["source"] = source
    return result
