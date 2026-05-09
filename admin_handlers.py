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

class AddServiceStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_duration = State()
    waiting_for_price = State()

class AddScheduleStates(StatesGroup):
    waiting_for_master = State()
    waiting_for_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()

@router.message(Command("admin"))
async def cmd_admin_panel(message: Message):
    """Панель администратора"""
    if is_admin(message.from_user.id):
        await message.answer(
            "👑 *Панель администратора*\n\n"
            "Выберите действие:",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "🔐 Эта команда доступна только администраторам.\n\n"
            "Если вы администратор, используйте команду:\n"
            "/becomeadmin КОД",
            reply_markup=get_admin_actions_keyboard()
        )

@router.message(Command("becomeadmin"))
async def cmd_become_admin(message: Message):
    """Стать администратором по коду"""
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Введите код: /becomeadmin КОД")
        return
    
    code = parts[1]
    ADMIN_SECRET_CODE = "SALON2026"
    
    if code == ADMIN_SECRET_CODE:
        add_admin(message.from_user.id)
        await message.answer(
            "✅ Вы стали администратором!\n\n"
            "Теперь вам доступны команды:\n"
            "/admin - панель администратора\n"
            "/add_master - добавить мастера\n"
            "/add_service - добавить услугу\n"
            "/add_schedule - добавить расписание\n"
            "/all_bookings - все записи"
        )
    else:
        await message.answer("❌ Неверный код")

@router.message(Command("add_master"))
@router.message(F.text == "➕ Добавить мастера")
async def cmd_add_master(message: Message, state: FSMContext):
    """Добавление нового мастера"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer("👨‍🎨 Введите имя мастера:")
    await state.set_state(AddMasterStates.waiting_for_name)

@router.message(AddMasterStates.waiting_for_name)
async def add_master_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📋 Введите специализацию мастера (например: Парикмахер-стилист):")
    await state.set_state(AddMasterStates.waiting_for_specialization)

@router.message(AddMasterStates.waiting_for_specialization)
async def add_master_specialization(message: Message, state: FSMContext):
    data = await state.get_data()
    add_master(data['name'], message.text)
    
    await message.answer(
        f"✅ Мастер {data['name']} добавлен!\n"
        f"Специализация: {message.text}",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@router.message(Command("add_service"))
@router.message(F.text == "➕ Добавить услугу")
async def cmd_add_service(message: Message, state: FSMContext):
    """Добавление новой услуги"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer("💇‍♀️ Введите название услуги:")
    await state.set_state(AddServiceStates.waiting_for_name)

@router.message(AddServiceStates.waiting_for_name)
async def add_service_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("⏱ Введите длительность в минутах (например: 60):")
    await state.set_state(AddServiceStates.waiting_for_duration)

@router.message(AddServiceStates.waiting_for_duration)
async def add_service_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text)
        await state.update_data(duration=duration)
        await message.answer("💰 Введите стоимость в рублях (например: 1500):")
        await state.set_state(AddServiceStates.waiting_for_price)
    except ValueError:
        await message.answer("❌ Введите число (минуты)")

@router.message(AddServiceStates.waiting_for_price)
async def add_service_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        data = await state.get_data()
        add_service(data['name'], data['duration'], price)
        
        await message.answer(
            f"✅ Услуга добавлена!\n\n"
            f"📋 {data['name']}\n"
            f"⏱ {data['duration']} мин\n"
            f"💰 {price}₽",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число (рубли)")

@router.message(Command("add_schedule"))
@router.message(F.text == "📅 Добавить расписание")
async def cmd_add_schedule(message: Message, state: FSMContext):
    """Добавление расписания мастера"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    masters = get_all_masters()
    text = "👨‍🎨 *Выберите мастера:*\n\n"
    for master in masters:
        text += f"ID: {master['master_id']} - {master['name']} ({master['specialization']})\n"
    
    text += "\nВведите ID мастера:"
    await message.answer(text, parse_mode="Markdown")
    await state.set_state(AddScheduleStates.waiting_for_master)

@router.message(AddScheduleStates.waiting_for_master)
async def add_schedule_master(message: Message, state: FSMContext):
    try:
        master_id = int(message.text)
        await state.update_data(master_id=master_id)
        await message.answer("📅 Введите дату в формате ГГГГ-ММ-ДД (например: 2026-05-15):")
        await state.set_state(AddScheduleStates.waiting_for_date)
    except ValueError:
        await message.answer("❌ Введите ID мастера (число)")

@router.message(AddScheduleStates.waiting_for_date)
async def add_schedule_date(message: Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text, "%Y-%m-%d").date()
        await state.update_data(date=message.text)
        await message.answer("⏰ Введите время начала в формате ЧЧ:ММ (например: 10:00):")
        await state.set_state(AddScheduleStates.waiting_for_start_time)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")

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

@router.message(Command("all_bookings"))
@router.message(F.text == "📋 Все записи")
async def cmd_all_bookings(message: Message):
    """Показать все записи (админ)"""
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
        text += f"   📞 {booking['phone']}\n"
        text += f"   💇‍♀️ {booking['service_name']}\n"
        text += f"   👨‍🎨 {booking['master_name']}\n"
        text += f"   📅 {booking['booking_date']}\n"
        text += f"   ⏰ {booking['booking_time']}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "👥 Управление админами")
async def cmd_manage_admins(message: Message):
    """Управление администраторами"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer(
        "👥 *Управление администраторами*\n\n"
        "Чтобы добавить администратора, используйте команду:\n"
        "/add_admin TELEGRAM_ID\n\n"
        "Например: /add_admin 123456789",
        parse_mode="Markdown"
    )

@router.message(Command("add_admin"))
async def cmd_add_admin(message: Message):
    """Добавить администратора по ID"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Используйте: /add_admin TELEGRAM_ID")
        return
    
    try:
        admin_id = int(parts[1])
        add_admin(admin_id)
        await message.answer(f"✅ Пользователь {admin_id} добавлен как администратор")
    except ValueError:
        await message.answer("❌ Неверный ID")