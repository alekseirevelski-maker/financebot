import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DB_PATH = os.getenv("DB_PATH", "data/finance.db")

# Proxy: xray SOCKS5 on localhost
PROXY_URL = os.getenv("PROXY_URL", "http://127.0.0.1:10809")

# Yandex Vision API (OCR чеков и скриншотов)
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
