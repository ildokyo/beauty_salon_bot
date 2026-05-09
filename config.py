import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_SECRET_CODE = os.getenv("ADMIN_SECRET_CODE", "SALON2026")