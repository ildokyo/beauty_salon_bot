import pytz
from datetime import datetime, timedelta

def get_izhevsk_now():
    """Возвращает текущее время в Ижевске (UTC+4)"""
    tz = pytz.timezone('Europe/Samara')
    return datetime.now(tz)

def format_date(date_str):
    """Приводит дату к формату ДД.ММ.ГГГГ"""
    try:
        # Если пришло в формате ГГГГ-ММ-ДД
        if '-' in date_str:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%d.%m.%Y")
        # Если уже в правильном формате
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        return date_str
    except:
        return date_str

def parse_date(date_str):
    """Преобразует ДД.ММ.ГГГГ в объект datetime"""
    try:
        # Если пришло в формате YYYY-MM-DD
        if '-' in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        # Если в формате DD.MM.YYYY
        return datetime.strptime(date_str, "%d.%m.%Y").date()
    except:
        return None

def get_tomorrow_str():
    """Возвращает завтрашнюю дату в формате ДД.ММ.ГГГГ"""
    tomorrow = get_izhevsk_now().date() + timedelta(days=1)
    return tomorrow.strftime("%d.%m.%Y")