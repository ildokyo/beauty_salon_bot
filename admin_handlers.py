import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import *
from keyboards import *

router = Router()
logger = logging.getLogger(__name__)

# Состояния для добавления
class AddMasterStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_specialization = State()
    waiting_for_category = State()

class AddServiceStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_duration = State()
    waiting_for_price = State()
    waiting_for_category = State()

class AddScheduleStates(StatesGroup):
    waiting_for_master = State()
    waiting_for_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()

class AddAdminStates(StatesGroup):
    waiting_for_id = State()

class RemoveAdminStates(StatesGroup):
    waiting_for_id = State()

# ============ КОМАНДЫ АДМИНИСТРАТОРА ============

@router.message(Command("admin"))
async def cmd_admin_panel(message: Message):
    if is_admin(message.from_user.id):
        await message.answer(
            "👑 *Панель администратора*\n\nВыберите действие:",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "🔐 Эта команда доступна только администраторам.\n\n"
            "Чтобы стать администратором, обратитесь к существующему админу.",
            reply_markup=get_main_keyboard()
        )

@router.message(Command("becomeadmin"))
async def cmd_become_admin(message: Message):
    """Стать администратором (только по приглашению существующего админа)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Только существующие администраторы могут добавлять новых.\nОбратитесь к тому, кто уже есть в админах.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Используйте: /becomeadmin TELEGRAM_ID")
        return
    
    try:
        new_admin_id = int(parts[1])
        add_admin(new_admin_id)
        await message.answer(f"✅ Пользователь {new_admin_id} добавлен как администратор")
    except ValueError:
        await message.answer("❌ Неверный ID")

@router.message(F.text == "🚪 Выйти из админки")
async def cmd_exit_admin(message: Message):
    """Выход из режима администратора (просто переключает клавиатуру)"""
    await message.answer(
        "Вы вышли из панели администратора 👋",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "◀️ Клиентское меню")
async def back_to_client_menu(message: Message):
    await message.answer("Возвращаемся в клиентское меню 👋", reply_markup=get_main_keyboard())

# ============ УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ ============

@router.message(F.text == "👥 Управление админами")
async def cmd_manage_admins(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer(
        "👥 *Управление администраторами*\n\n"
        "Выберите действие:",
        reply_markup=get_admin_management_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "➕ Добавить админа")
async def cmd_add_admin_prompt(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer(
        "📝 Введите Telegram ID нового администратора\n\n"
        "Как узнать ID: @userinfobot\n\n"
        "Или нажмите «Отмена»",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AddAdminStates.waiting_for_id)

@router.message(AddAdminStates.waiting_for_id)
async def process_add_admin(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        admin_id = int(message.text.strip())
        add_admin(admin_id)
        await message.answer(f"✅ Пользователь {admin_id} добавлен как администратор", reply_markup=get_admin_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный ID. Введите число.", reply_markup=get_cancel_keyboard())

@router.message(F.text == "🗑 Удалить админа")
async def cmd_remove_admin_prompt(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    admins = get_all_admins()
    if not admins:
        await message.answer("📭 Нет администраторов для удаления")
        return
    
    text = "📋 *Список администраторов:*\n\n"
    for admin in admins:
        text += f"• ID: `{admin['telegram_id']}`\n"
    
    text += "\nВведите Telegram ID для удаления:"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_cancel_keyboard())
    await state.set_state(RemoveAdminStates.waiting_for_id)

@router.message(RemoveAdminStates.waiting_for_id)
async def process_remove_admin(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Удаление отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        admin_id = int(message.text.strip())
        
        # Нельзя удалить самого себя
        if admin_id == message.from_user.id:
            await message.answer("❌ Нельзя удалить самого себя", reply_markup=get_admin_keyboard())
            await state.clear()
            return
        
        if remove_admin(admin_id):
            await message.answer(f"✅ Администратор {admin_id} удалён", reply_markup=get_admin_keyboard())
        else:
            await message.answer(f"❌ Администратор {admin_id} не найден", reply_markup=get_admin_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный ID. Введите число.", reply_markup=get_cancel_keyboard())

@router.message(F.text == "📋 Список админов")
async def cmd_list_admins(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    admins = get_all_admins()
    
    if not admins:
        await message.answer("📭 Нет администраторов")
        return
    
    text = "👥 *Список администраторов:*\n\n"
    for admin in admins:
        text += f"• ID: `{admin['telegram_id']}`\n"
    
    text += "\nЧтобы удалить админа, используйте «🗑 Удалить админа»"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_admin_management_keyboard())

@router.message(F.text == "🔙 Назад в админку")
async def back_to_admin(message: Message):
    await message.answer("Возврат в панель администратора", reply_markup=get_admin_keyboard())

# ============ ДОБАВЛЕНИЕ МАСТЕРОВ ============

@router.message(Command("add_master"))
@router.message(F.text == "➕ Добавить мастера")
async def cmd_add_master(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer("👨‍🎨 Введите имя мастера:", reply_markup=get_cancel_keyboard())
    await state.set_state(AddMasterStates.waiting_for_name)

@router.message(AddMasterStates.waiting_for_name)
async def add_master_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление отменено", reply_markup=get_admin_keyboard())
        return
    
    await state.update_data(name=message.text)
    await message.answer("📋 Введите специализацию (например: Парикмахер-стилист):")
    await state.set_state(AddMasterStates.waiting_for_specialization)

@router.message(AddMasterStates.waiting_for_specialization)
async def add_master_specialization(message: Message, state: FSMContext):
    await state.update_data(specialization=message.text)
    await message.answer(
        "📂 Выберите категорию услуг:\n\n"
        "• hair - для парикмахерских услуг\n"
        "• nails - для маникюра/педикюра\n\n"
        "Введите: hair или nails"
    )
    await state.set_state(AddMasterStates.waiting_for_category)

@router.message(AddMasterStates.waiting_for_category)
async def add_master_category(message: Message, state: FSMContext):
    category = message.text.lower()
    if category not in ['hair', 'nails']:
        await message.answer("❌ Введите 'hair' или 'nails'")
        return
    
    data = await state.get_data()
    add_master(data['name'], data['specialization'], category)
    
    await message.answer(
        f"✅ Мастер {data['name']} добавлен!\n"
        f"Специализация: {data['specialization']}\n"
        f"Категория: {category}",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

# ============ ДОБАВЛЕНИЕ УСЛУГ ============

@router.message(Command("add_service"))
@router.message(F.text == "➕ Добавить услугу")
async def cmd_add_service(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer("💇‍♀️ Введите название услуги:", reply_markup=get_cancel_keyboard())
    await state.set_state(AddServiceStates.waiting_for_name)

@router.message(AddServiceStates.waiting_for_name)
async def add_service_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление отменено", reply_markup=get_admin_keyboard())
        return
    
    await state.update_data(name=message.text)
    await message.answer("⏱ Введите длительность в минутах:")
    await state.set_state(AddServiceStates.waiting_for_duration)

@router.message(AddServiceStates.waiting_for_duration)
async def add_service_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text)
        await state.update_data(duration=duration)
        await message.answer("💰 Введите стоимость в рублях:")
        await state.set_state(AddServiceStates.waiting_for_price)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(AddServiceStates.waiting_for_price)
async def add_service_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price=price)
        await message.answer(
            "📂 Выберите категорию:\n\n"
            "• hair - парикмахерские услуги\n"
            "• nails - маникюр/педикюр\n\n"
            "Введите: hair или nails"
        )
        await state.set_state(AddServiceStates.waiting_for_category)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(AddServiceStates.waiting_for_category)
async def add_service_category(message: Message, state: FSMContext):
    category = message.text.lower()
    if category not in ['hair', 'nails']:
        await message.answer("❌ Введите 'hair' или 'nails'")
        return
    
    data = await state.get_data()
    add_service(data['name'], data['duration'], data['price'], category)
    
    await message.answer(
        f"✅ Услуга добавлена!\n\n"
        f"📋 {data['name']}\n"
        f"⏱ {data['duration']} мин\n"
        f"💰 {data['price']}₽\n"
        f"📂 Категория: {category}",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

# ============ ДОБАВЛЕНИЕ РАСПИСАНИЯ ============

@router.message(Command("add_schedule"))
@router.message(F.text == "📅 Добавить расписание")
async def cmd_add_schedule(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    masters = get_all_masters()
    text = "👨‍🎨 *Выберите мастера (введите ID):*\n\n"
    for master in masters:
        text += f"ID: {master['master_id']} - {master['name']} ({master['specialization']})\n"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_cancel_keyboard())
    await state.set_state(AddScheduleStates.waiting_for_master)

@router.message(AddScheduleStates.waiting_for_master)
async def add_schedule_master(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        master_id = int(message.text)
        await state.update_data(master_id=master_id)
        await message.answer("📅 Введите дату в формате ДД.ММ.ГГГГ (например: 25.05.2026):")
        await state.set_state(AddScheduleStates.waiting_for_date)
    except ValueError:
        await message.answer("❌ Введите ID мастера (число)", reply_markup=get_cancel_keyboard())

@router.message(AddScheduleStates.waiting_for_date)
async def add_schedule_date(message: Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(date=message.text)
        await message.answer("⏰ Введите время начала в формате ЧЧ:ММ (например: 10:00):")
        await state.set_state(AddScheduleStates.waiting_for_start_time)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ")

@router.message(AddScheduleStates.waiting_for_start_time)
async def add_schedule_start(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%H:%M")
        await state.update_data(start_time=message.text)
        await message.answer("⏰ Введите время окончания в формате ЧЧ:ММ (например: 18:00):")
        await state.set_state(AddScheduleStates.waiting_for_end_time)
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ")

@router.message(AddScheduleStates.waiting_for_end_time)
async def add_schedule_end(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%H:%M")
        data = await state.get_data()
        
        slots_count = add_work_slots(
            data['master_id'],
            data['date'],
            data['start_time'],
            message.text
        )
        
        await message.answer(
            f"✅ Расписание добавлено!\n\n"
            f"👨‍🎨 Мастер ID: {data['master_id']}\n"
            f"📅 Дата: {data['date']}\n"
            f"⏰ Время: {data['start_time']} - {message.text}\n"
            f"📊 Создано слотов: {slots_count}",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ")

# ============ ПРОСМОТР ВСЕХ ЗАПИСЕЙ ============

@router.message(Command("all_bookings"))
@router.message(F.text == "📋 Все записи")
async def cmd_all_bookings(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    bookings = get_all_bookings_admin()
    
    if not bookings:
        await message.answer("📭 Нет активных записей")
        return
    
    text = "📋 *Все активные записи:*\n\n"
    for booking in bookings:
        text += f"🔹 Запись #{booking['booking_id']}\n"
        text += f"   Клиент: {booking['client_name']}\n"
        text += f"   📞 {booking['phone'] or 'не указан'}\n"
        text += f"   💇‍♀️ {booking['service_name']}\n"
        text += f"   👨‍🎨 {booking['master_name']}\n"
        text += f"   📅 {booking['booking_date']}\n"
        text += f"   ⏰ {booking['booking_time']}\n\n"
        
        if len(text) > 3000:
            await message.answer(text, parse_mode="Markdown")
            text = ""
    
    if text:
        await message.answer(text, parse_mode="Markdown")