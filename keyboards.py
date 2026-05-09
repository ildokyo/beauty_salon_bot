from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    """Главная клавиатура для клиента"""
    kb = [
        [KeyboardButton(text="💇‍♀️ Услуги"), KeyboardButton(text="👨‍🎨 Мастера")],
        [KeyboardButton(text="📅 Записаться"), KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="ℹ️ О салоне"), KeyboardButton(text="📞 Контакты")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_keyboard():
    """Клавиатура для администратора"""
    kb = [
        [KeyboardButton(text="➕ Добавить мастера"), KeyboardButton(text="➕ Добавить услугу")],
        [KeyboardButton(text="📅 Добавить расписание"), KeyboardButton(text="📋 Все записи")],
        [KeyboardButton(text="👥 Управление админами"), KeyboardButton(text="🚪 Выйти из админки")],
        [KeyboardButton(text="◀️ Клиентское меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_keyboard():
    """Клавиатура с кнопкой Отмена"""
    kb = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_back_keyboard():
    """Клавиатура с кнопкой Назад"""
    kb = [[KeyboardButton(text="🔙 Назад")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_services_inline_keyboard(services):
    """Инлайн-клавиатура для выбора услуги"""
    keyboard = []
    for service in services:
        btn_text = f"{service['name']} - {service['price']}₽ ({service['duration_min']} мин)"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"service_{service['service_id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_masters_inline_keyboard(masters):
    """Инлайн-клавиатура для выбора мастера"""
    keyboard = []
    for master in masters:
        keyboard.append([InlineKeyboardButton(
            text=f"👨‍🎨 {master['name']} - {master['specialization']}",
            callback_data=f"master_{master['master_id']}"
        )])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_services")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_slots_inline_keyboard(slots):
    """Инлайн-клавиатура для выбора времени"""
    keyboard = []
    for slot in slots:
        keyboard.append([InlineKeyboardButton(
            text=f"⏰ {slot['time_start']}",
            callback_data=f"slot_{slot['schedule_id']}"
        )])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_masters")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_booking_actions_keyboard(booking_id):
    """Инлайн-клавиатура для действий с записью"""
    keyboard = [
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_booking_{booking_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_management_keyboard():
    """Клавиатура управления администраторами"""
    kb = [
        [KeyboardButton(text="➕ Добавить админа")],
        [KeyboardButton(text="🗑 Удалить админа")],
        [KeyboardButton(text="📋 Список админов")],
        [KeyboardButton(text="🔙 Назад в админку")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)