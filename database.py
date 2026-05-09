import sqlite3
import logging
from datetime import datetime, timedelta

DB_NAME = "beauty_salon.db"
logger = logging.getLogger(__name__)

def get_db_connection():
    """Возвращает соединение с базой данных"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Создаёт все таблицы, если их нет"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица клиентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
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
        
        # Добавляем тестовые данные, если таблицы пустые
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            services_data = [
                ("Стрижка женская", 60, 1500),
                ("Стрижка мужская", 30, 800),
                ("Окрашивание", 120, 3000),
                ("Маникюр", 60, 1200),
                ("Педикюр", 90, 1800),
                ("Укладка", 45, 1000),
            ]
            cursor.executemany(
                "INSERT INTO services (name, duration_min, price) VALUES (?, ?, ?)",
                services_data
            )
        
        cursor.execute("SELECT COUNT(*) FROM masters")
        if cursor.fetchone()[0] == 0:
            masters_data = [
                ("Анна", "Парикмахер-стилист"),
                ("Елена", "Мастер маникюра"),
                ("Мария", "Колорист"),
                ("Ольга", "Мастер педикюра"),
            ]
            cursor.executemany(
                "INSERT INTO masters (name, specialization) VALUES (?, ?)",
                masters_data
            )
        
        conn.commit()
        logger.info("База данных инициализирована")

# ============ ФУНКЦИИ ДЛЯ КЛИЕНТОВ ============

def add_client(telegram_id, name, phone=None):
    """Добавляет нового клиента"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO clients (telegram_id, name, phone)
            VALUES (?, ?, ?)
        ''', (telegram_id, name, phone))
        conn.commit()
        return cursor.lastrowid

def get_client(telegram_id):
    """Получает информацию о клиенте"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE telegram_id = ?', (telegram_id,))
        return cursor.fetchone()

def get_all_services():
    """Получает список всех активных услуг"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM services WHERE is_active = 1 ORDER BY price')
        return cursor.fetchall()

def get_service(service_id):
    """Получает услугу по ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM services WHERE service_id = ?', (service_id,))
        return cursor.fetchone()

def get_all_masters():
    """Получает список всех активных мастеров"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM masters WHERE is_active = 1')
        return cursor.fetchall()

def get_master(master_id):
    """Получает мастера по ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM masters WHERE master_id = ?', (master_id,))
        return cursor.fetchone()

def get_free_slots(master_id, date):
    """Получает свободные слоты мастера на конкретную дату"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM master_schedule 
            WHERE master_id = ? AND work_date = ? AND is_booked = 0
            ORDER BY time_start
        ''', (master_id, date))
        return cursor.fetchall()

def add_booking(client_id, master_id, service_id, schedule_id, date, time):
    """Создаёт новую запись"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Помечаем слот как занятый
        cursor.execute('''
            UPDATE master_schedule 
            SET is_booked = 1, booking_id = ?
            WHERE schedule_id = ?
        ''', (cursor.lastrowid, schedule_id))
        
        # Создаём запись
        cursor.execute('''
            INSERT INTO bookings (client_id, master_id, service_id, schedule_id, booking_date, booking_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (client_id, master_id, service_id, schedule_id, date, time))
        
        conn.commit()
        return cursor.lastrowid

def get_client_bookings(telegram_id):
    """Получает все записи клиента"""
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
    """Отменяет запись"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Получаем schedule_id
        cursor.execute('SELECT schedule_id FROM bookings WHERE booking_id = ? AND client_id = ?', 
                      (booking_id, client_id))
        result = cursor.fetchone()
        
        if result:
            # Освобождаем слот
            cursor.execute('''
                UPDATE master_schedule 
                SET is_booked = 0, booking_id = NULL
                WHERE schedule_id = ?
            ''', (result['schedule_id'],))
            
            # Отменяем запись
            cursor.execute('''
                UPDATE bookings SET status = 'cancelled'
                WHERE booking_id = ?
            ''', (booking_id,))
            
            conn.commit()
            return True
        return False

def get_tomorrow_bookings():
    """Получает записи на завтра для напоминаний"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
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
        ''', (tomorrow,))
        return cursor.fetchall()

# ============ ФУНКЦИИ ДЛЯ АДМИНИСТРАТОРОВ ============

def is_admin(telegram_id):
    """Проверяет, является ли пользователь администратором"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admins WHERE telegram_id = ?', (telegram_id,))
        return cursor.fetchone() is not None

def add_admin(telegram_id):
    """Добавляет администратора"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)', (telegram_id,))
        conn.commit()

def add_master(name, specialization):
    """Добавляет нового мастера"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO masters (name, specialization) VALUES (?, ?)', 
                      (name, specialization))
        conn.commit()
        return cursor.lastrowid

def add_service(name, duration_min, price):
    """Добавляет новую услугу"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO services (name, duration_min, price) 
            VALUES (?, ?, ?)
        ''', (name, duration_min, price))
        conn.commit()
        return cursor.lastrowid

def add_work_slots(master_id, date, start_time, end_time, interval_min=30):
    """Добавляет рабочие слоты мастера на конкретную дату"""
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
            ''', (master_id, date, time_str, 
                  (current + timedelta(minutes=interval_min)).strftime("%H:%M")))
            slots_added += cursor.rowcount
            current += timedelta(minutes=interval_min)
        
        conn.commit()
        return slots_added

def get_all_bookings_admin():
    """Получает все записи (для администратора)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, c.name as client_name, c.phone,
                   s.name as service_name, m.name as master_name
            FROM bookings b
            JOIN clients c ON b.client_id = c.client_id
            JOIN services s ON b.service_id = s.service_id
            JOIN masters m ON b.master_id = m.master_id
            WHERE b.status = 'confirmed'
            ORDER BY b.booking_date, b.booking_time
        ''')
        return cursor.fetchall()