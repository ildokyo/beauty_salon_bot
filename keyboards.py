from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    kb = [
        [KeyboardButton(text="💇‍♀️ Услуги"), KeyboardButton(text="👨‍🎨 Мастера")],
        [KeyboardButton(text="📅 Записаться"), KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="ℹ️ О салоне"), KeyboardButton(text="📞 Контакты")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_keyboard():
    kb = [
        [KeyboardButton(text="👨‍🎨 Управление мастерами")],
        [KeyboardButton(text="➕ Добавить услугу"), KeyboardButton(text="📅 Добавить расписание")],
        [KeyboardButton(text="📋 Все записи"), KeyboardButton(text="👥 Управление админами")],
        [KeyboardButton(text="🚪 Выйти из админки"), KeyboardButton(text="◀️ Клиентское меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_masters_management_keyboard():
    kb = [
        [KeyboardButton(text="➕ Добавить мастера")],
        [KeyboardButton(text="🗑 Удалить мастера")],
        [KeyboardButton(text="🔄 Восстановить мастера")],
        [KeyboardButton(text="📋 Список мастеров")],
        [KeyboardButton(text="🔙 Назад в админку")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_management_keyboard():
    kb = [
        [KeyboardButton(text="➕ Добавить админа")],
        [KeyboardButton(text="🗑 Удалить админа")],
        [KeyboardButton(text="📋 Список админов")],
        [KeyboardButton(text="🔙 Назад в админку")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_keyboard():
    kb = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_services_inline_keyboard(services):
    keyboard = []
    for service in services:
        btn_text = f"{service['name']} - {service['price']}₽ ({service['duration_min']} мин)"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"service_{service['service_id']}")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_masters_inline_keyboard(masters):
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
    keyboard = [
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_booking_{booking_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)