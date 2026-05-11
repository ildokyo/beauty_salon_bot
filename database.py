import sqlite3
import logging
import math
from datetime import datetime, timedelta
from utils import get_izhevsk_now, format_date

DB_NAME = "beauty_salon.db"
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица клиентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                name TEXT NOT NULL,
                phone TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица мастеров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS masters (
                master_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialization TEXT,
                experience TEXT,
                service_category TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица услуг
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                service_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                duration_min INTEGER NOT NULL,
                price INTEGER NOT NULL,
                category TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица расписания мастеров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS master_schedule (
                schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                master_id INTEGER NOT NULL,
                work_date TEXT NOT NULL,
                time_start TEXT NOT NULL,
                time_end TEXT NOT NULL,
                is_booked INTEGER DEFAULT 0,
                booking_id INTEGER,
                FOREIGN KEY (master_id) REFERENCES masters(master_id)
            )
        ''')
        
        # Таблица записей клиентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                master_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                schedule_id INTEGER NOT NULL,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                status TEXT DEFAULT 'confirmed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(client_id),
                FOREIGN KEY (master_id) REFERENCES masters(master_id),
                FOREIGN KEY (service_id) REFERENCES services(service_id),
                FOREIGN KEY (schedule_id) REFERENCES master_schedule(schedule_id)
            )
        ''')
        
        # Таблица администраторов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL
            )
        ''')
        
        # Добавляем тестовые данные
        cursor.execute("SELECT COUNT(*) FROM masters")
        if cursor.fetchone()[0] == 0:
            masters_data = [
                ("Анна Петрова", "Парикмахер-стилист", "8 лет", "hair"),
                ("Елена Смирнова", "Старший парикмахер", "12 лет", "hair"),
                ("Мария Иванова", "Мастер маникюра", "5 лет", "nails"),
                ("Ольга Кузнецова", "Мастер педикюра", "7 лет", "nails"),
            ]
            cursor.executemany(
                "INSERT INTO masters (name, specialization, experience, service_category) VALUES (?, ?, ?, ?)",
                masters_data
            )
        
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            services_data = [
                ("💇‍♀️ Стрижка женская", 60, 1500, "hair"),
                ("💇‍♂️ Стрижка мужская", 30, 800, "hair"),
                ("🎨 Окрашивание", 120, 3000, "hair"),
                ("💨 Укладка", 45, 1000, "hair"),
                ("💅 Маникюр", 60, 1200, "nails"),
                ("🦶 Педикюр", 90, 1800, "nails"),
                ("✨ Покрытие гель-лак", 60, 1500, "nails"),
            ]
            cursor.executemany(
                "INSERT INTO services (name, duration_min, price, category) VALUES (?, ?, ?, ?)",
                services_data
            )
        
        conn.commit()
        logger.info("База данных инициализирована")

# ============ ФУНКЦИИ ДЛЯ КЛИЕНТОВ ============

def add_client(telegram_id, name, phone=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO clients (telegram_id, name, phone)
            VALUES (?, ?, ?)
        ''', (telegram_id, name, phone))
        conn.commit()
        return cursor.lastrowid

def get_client(telegram_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE telegram_id = ?', (telegram_id,))
        return cursor.fetchone()

def get_all_services():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM services WHERE is_active = 1 ORDER BY price')
        return cursor.fetchall()

def get_service(service_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM services WHERE service_id = ?', (service_id,))
        row = cursor.fetchone()
        if row:
            return dict(row) 
        return None

def get_master(master_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM masters WHERE master_id = ?', (master_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_masters_by_category(category):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM masters WHERE service_category = ? AND is_active = 1', (category,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_all_masters(include_inactive=False):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if include_inactive:
            cursor.execute('SELECT * FROM masters ORDER BY master_id')
        else:
            cursor.execute('SELECT * FROM masters WHERE is_active = 1 ORDER BY master_id')
        return cursor.fetchall()

def get_active_masters():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM masters WHERE is_active = 1 ORDER BY master_id')
        return cursor.fetchall()

def get_free_slots(master_id, date_str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT schedule_id, time_start, time_end 
            FROM master_schedule 
            WHERE master_id = ? AND work_date = ? AND is_booked = 0
            ORDER BY time_start
        ''', (master_id, date_str))
        slots = cursor.fetchall()
        return slots

def add_booking_with_duration(client_id, master_id, service_id, schedule_id, date, time, duration_min):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT time_start, time_end FROM master_schedule WHERE schedule_id = ?', (schedule_id,))
        slot = cursor.fetchone()
        
        if not slot:
            return None
        
        slots_to_block = math.ceil(duration_min / 30)
        
        cursor.execute('''
            SELECT schedule_id, time_start 
            FROM master_schedule 
            WHERE master_id = ? AND work_date = ? AND time_start >= ? AND is_booked = 0
            ORDER BY time_start
            LIMIT ?
        ''', (master_id, date, slot['time_start'], slots_to_block))
        
        slots = cursor.fetchall()
        
        if len(slots) < slots_to_block:
            return None
        
        for s in slots:
            cursor.execute('''
                UPDATE master_schedule 
                SET is_booked = 1, booking_id = ?
                WHERE schedule_id = ?
            ''', (cursor.lastrowid, s['schedule_id']))
        
        cursor.execute('''
            INSERT INTO bookings (client_id, master_id, service_id, schedule_id, booking_date, booking_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (client_id, master_id, service_id, schedule_id, date, time))
        
        conn.commit()
        return cursor.lastrowid

def get_client_bookings(telegram_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, s.name as service_name, m.name as master_name, s.price
            FROM bookings b
            JOIN clients c ON b.client_id = c.client_id
            JOIN services s ON b.service_id = s.service_id
            JOIN masters m ON b.master_id = m.master_id
            WHERE c.telegram_id = ? AND b.status = 'confirmed'
            ORDER BY b.booking_date, b.booking_time
        ''', (telegram_id,))
        return cursor.fetchall()

def cancel_booking(booking_id, client_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT schedule_id FROM bookings WHERE booking_id = ? AND client_id = ?', 
                      (booking_id, client_id))
        result = cursor.fetchone()
        
        if result:
            cursor.execute('''
                UPDATE master_schedule 
                SET is_booked = 0, booking_id = NULL
                WHERE schedule_id = ?
            ''', (result['schedule_id'],))
            
            cursor.execute('''
                UPDATE bookings SET status = 'cancelled'
                WHERE booking_id = ?
            ''', (booking_id,))
            
            conn.commit()
            return True
        return False

def get_tomorrow_bookings():
    # Получает все записи на завтра для отправки напоминаний
    from datetime import datetime, timedelta
    from utils import get_izhevsk_now
    
    tomorrow = get_izhevsk_now().date() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%d.%m.%Y")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, c.telegram_id, c.name as client_name,
                   s.name as service_name, m.name as master_name
            FROM bookings b
            JOIN clients c ON b.client_id = c.client_id
            JOIN services s ON b.service_id = s.service_id
            JOIN masters m ON b.master_id = m.master_id
            WHERE b.booking_date = ? AND b.status = 'confirmed'
        ''', (tomorrow_str,))
        return cursor.fetchall()

def get_all_clients():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT telegram_id, name FROM clients')
        return cursor.fetchall()

# ============ ФУНКЦИИ ДЛЯ АДМИНИСТРАТОРОВ ============

def is_admin(telegram_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admins WHERE telegram_id = ?', (telegram_id,))
        return cursor.fetchone() is not None

def add_admin(telegram_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)', (telegram_id,))
        conn.commit()

def remove_admin(telegram_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM admins WHERE telegram_id = ?', (telegram_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_all_admins():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admins')
        return cursor.fetchall()

def get_all_admins_with_names():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.telegram_id, c.name 
            FROM admins a
            LEFT JOIN clients c ON a.telegram_id = c.telegram_id
        ''')
        return cursor.fetchall()

def delete_master(master_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE masters SET is_active = 0 WHERE master_id = ?', (master_id,))
        conn.commit()
        return cursor.rowcount > 0

def restore_master(master_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE masters SET is_active = 1 WHERE master_id = ?', (master_id,))
        conn.commit()
        return cursor.rowcount > 0

def add_master(name, specialization, experience, category):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO masters (name, specialization, experience, service_category) 
            VALUES (?, ?, ?, ?)
        ''', (name, specialization, experience, category))
        conn.commit()
        return cursor.lastrowid

def delete_service(service_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE services SET is_active = 0 WHERE service_id = ?', (service_id,))
        conn.commit()
        return cursor.rowcount > 0

def restore_service(service_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE services SET is_active = 1 WHERE service_id = ?', (service_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_all_services_with_inactive():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM services ORDER BY service_id')
        return cursor.fetchall()

def add_service(name, duration_min, price, category):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO services (name, duration_min, price, category) 
            VALUES (?, ?, ?, ?)
        ''', (name, duration_min, price, category))
        conn.commit()
        return cursor.lastrowid

def add_work_slots(master_id, date, start_time, end_time, interval_min=30):
    date_obj = datetime.strptime(date, "%d.%m.%Y")
    date_db = date_obj.strftime("%d.%m.%Y")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        current = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")
        
        slots_added = 0
        while current + timedelta(minutes=interval_min) <= end:
            time_str = current.strftime("%H:%M")
            cursor.execute('''
                INSERT OR IGNORE INTO master_schedule (master_id, work_date, time_start, time_end)
                VALUES (?, ?, ?, ?)
            ''', (master_id, date_db, time_str, 
                  (current + timedelta(minutes=interval_min)).strftime("%H:%M")))
            slots_added += cursor.rowcount
            current += timedelta(minutes=interval_min)
        
        conn.commit()
        return slots_added

def get_all_bookings_admin():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, c.name as client_name, c.phone, c.telegram_id,
                   s.name as service_name, m.name as master_name
            FROM bookings b
            JOIN clients c ON b.client_id = c.client_id
            JOIN services s ON b.service_id = s.service_id
            JOIN masters m ON b.master_id = m.master_id
            WHERE b.status = 'confirmed'
            ORDER BY b.booking_date, b.booking_time
        ''')
        return cursor.fetchall()