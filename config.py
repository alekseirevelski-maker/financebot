import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DB_PATH = os.getenv("DB_PATH", "data/finance.db")

# Proxy: xray SOCKS5 on localhost (empty = no proxy)
PROXY_URL = os.getenv("PROXY_URL", "")

# Yandex Vision API (OCR чеков и скриншотов)
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")

# Access control — whitelist user IDs (empty = dev mode, everyone allowed)
ALLOWED_USER_IDS: list[int] = [
    int(x.strip())
    for x in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if x.strip()
]

# Timezone
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
