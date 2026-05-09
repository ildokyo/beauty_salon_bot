import os
from dotenv import load_dotenv

# Эта конструкция работает и локально, и на сервере
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_SECRET_CODE = os.getenv("ADMIN_SECRET_CODE", "SALON2026")

# Добавьте это для удобства работы с файлом БД
DB_NAME = "beauty_salon.db"