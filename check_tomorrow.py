from database import get_db_connection
from datetime import datetime, timedelta

# Завтрашняя дата в формате ДД.ММ.ГГГГ
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
print(f"Завтра: {tomorrow}")

# Проверяем записи на завтра
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, c.telegram_id, c.name 
        FROM bookings b
        JOIN clients c ON b.client_id = c.client_id
        WHERE b.booking_date = ? AND b.status = 'confirmed'
    ''', (tomorrow,))
    bookings = cursor.fetchall()
    
    print(f"Найдено записей на завтра: {len(bookings)}")
    for b in bookings:
        print(f"  - Клиент: {b['name']}, Telegram ID: {b['telegram_id']}, Время: {b['booking_time']}")