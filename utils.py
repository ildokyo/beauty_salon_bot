import pytz
from datetime import datetime

def get_izhevsk_now():
    """Возвращает текущее время в Ижевске (UTC+4)"""
    tz = pytz.timezone('Europe/Samara')
    return datetime.now(tz)