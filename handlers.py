import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import *
from keyboards import *
from utils import get_izhevsk_now

router = Router()
logger = logging.getLogger(__name__)

# Состояния FSM для записи
class BookingStates(StatesGroup):
    waiting_for_service = State()
    waiting_for_master = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_phone = State()

# Вспомогательные функции
def get_available_dates():
    """Возвращает список доступных дат на 14 дней вперёд"""
    dates = []
    today = get_izhevsk_now().date()
    for i in range(14):
        date = today + timedelta(days=i)
        dates.append(date.strftime("%Y-%m-%d"))
    return dates

# ============ ОСНОВНЫЕ КОМАНДЫ ============

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user = message.from_user
    client = get_client(user.id)
    
    if not client:
        add_client(user.id, user.first_name)
        await message.answer(
            f"👋 Добро пожаловать в салон красоты «Элеганс», {user.first_name}!\n\n"
            f"Я помогу вам записаться к мастеру, узнать об услугах и не пропустить визит.\n\n"
            f"💇‍♀️ Нажмите «Услуги», чтобы посмотреть цены\n"
            f"📅 «Записаться» — чтобы выбрать время\n"
            f"📋 «Мои записи» — чтобы посмотреть или отменить запись"
        )
    else:
        await message.answer(
            f"С возвращением, {user.first_name}! 👋\n"
            f"Чем могу помочь сегодня?"
        )
    
    await message.answer(
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь"""
    help_text = """
📖 *Команды бота:*

/start — начать работу
/services — список услуг
/masters — список мастеров
/book — записаться на услугу
/mybookings — мои записи
/cancel — отменить запись
/help — эта справка

📞 *Контакты салона:*
Телефон: +7 (912) 123-45-67
Адрес: ул. Пушкинская, 123
    """
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("services"))
@router.message(F.text == "💇‍♀️ Услуги")
async def cmd_services(message: Message):
    """Показать услуги"""
    services = get_all_services()
    
    if not services:
        await message.answer("😔 Услуги временно не добавлены")
        return
    
    text = "💇‍♀️ *Наши услуги и цены:*\n\n"
    for service in services:
        text += f"✂️ *{service['name']}*\n"
        text += f"   ⏱ {service['duration_min']} мин | 💰 {service['price']}₽\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("masters"))
@router.message(F.text == "👨‍🎨 Мастера")
async def cmd_masters(message: Message):
    """Показать мастеров"""
    masters = get_all_masters()
    
    text = "👨‍🎨 *Наши мастера:*\n\n"
    for master in masters:
        text += f"✨ *{master['name']}*\n"
        text += f"   Специализация: {master['specialization']}\n"
        text += f"   ⭐ Стаж: от 5 лет\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("book"))
@router.message(F.text == "📅 Записаться")
async def cmd_book_start(message: Message, state: FSMContext):
    """Начать запись на услугу"""
    services = get_all_services()
    
    if not services:
        await message.answer("😔 Услуги временно недоступны")
        return
    
    await message.answer(
        "💇‍♀️ *Выберите услугу:*\n\n"
        "Нажмите на нужную услугу, чтобы продолжить",
        reply_markup=get_services_inline_keyboard(services),
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.waiting_for_service)

@router.callback_query(BookingStates.waiting_for_service, F.data.startswith("service_"))
async def process_service_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора услуги"""
    service_id = int(callback.data.split("_")[1])
    service = get_service(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена")
        return
    
    await state.update_data(service_id=service_id, service_name=service['name'])
    
    masters = get_all_masters()
    await callback.message.edit_text(
        f"✅ Выбрана услуга: *{service['name']}*\n"
        f"💰 Цена: {service['price']}₽\n"
        f"⏱ Длительность: {service['duration_min']} мин\n\n"
        f"👨‍🎨 *Выберите мастера:*",
        reply_markup=get_masters_inline_keyboard(masters),
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.waiting_for_master)
    await callback.answer()

@router.callback_query(BookingStates.waiting_for_master, F.data.startswith("master_"))
async def process_master_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора мастера"""
    master_id = int(callback.data.split("_")[1])
    master = get_master(master_id)
    
    await state.update_data(master_id=master_id, master_name=master['name'])
    
    # Запрашиваем дату
    dates = get_available_dates()
    dates_text = "\n".join([f"• {d}" for d in dates[:7]])
    
    await callback.message.edit_text(
        f"✅ Выбран мастер: *{master['name']}*\n\n"
        f"📅 *Доступные даты:*\n{dates_text}\n\n"
        f"Пожалуйста, напишите желаемую дату в формате ГГГГ-ММ-ДД\n"
        f"Например: 2026-05-15",
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.waiting_for_date)
    await callback.answer()

@router.message(BookingStates.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    """Обработка выбора даты"""
    date_str = message.text.strip()
    
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = get_izhevsk_now().date()
        
        if selected_date < today:
            await message.answer("❌ Нельзя выбрать прошедшую дату. Выберите дату от сегодняшней")
            return
        
        if selected_date > today + timedelta(days=14):
            await message.answer("❌ Можно записаться только на 14 дней вперёд")
            return
        
    except ValueError:
        await message.answer("❌ Неверный формат даты. Введите в формате ГГГГ-ММ-ДД\nНапример: 2026-05-15")
        return
    
    await state.update_data(booking_date=date_str)
    
    data = await state.get_data()
    free_slots = get_free_slots(data['master_id'], date_str)
    
    if not free_slots:
        await message.answer(
            f"😔 На {date_str} нет свободных слотов у мастера {data['master_name']}.\n"
            f"Пожалуйста, выберите другую дату (команда /book)"
        )
        await state.clear()
        return
    
    await message.answer(
        f"📅 Дата: {date_str}\n\n"
        f"⏰ *Выберите удобное время:*",
        reply_markup=get_slots_inline_keyboard(free_slots),
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.waiting_for_time)

@router.callback_query(BookingStates.waiting_for_time, F.data.startswith("slot_"))
async def process_slot_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени"""
    schedule_id = int(callback.data.split("_")[1])
    await state.update_data(schedule_id=schedule_id)
    
    # Запрашиваем телефон
    await callback.message.edit_text(
        f"✅ Время выбрано!\n\n"
        f"📱 *Укажите ваш номер телефона*\n"
        f"Мы не будем звонить без необходимости, только для подтверждения записи\n\n"
        f"Пример: +7 (912) 123-45-67",
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.waiting_for_phone)
    await callback.answer()

@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Сохранение телефона и создание записи"""
    phone = message.text.strip()
    data = await state.get_data()
    
    client = get_client(message.from_user.id)
    
    if client and not client['phone']:
        # Обновляем телефон клиента
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE clients SET phone = ? WHERE telegram_id = ?', 
                          (phone, message.from_user.id))
            conn.commit()
    
    # Создаём запись
    booking_id = add_booking(
        client_id=client['client_id'],
        master_id=data['master_id'],
        service_id=data['service_id'],
        schedule_id=data['schedule_id'],
        date=data['booking_date'],
        time=""
    )
    
    # Получаем информацию о слоте
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT time_start FROM master_schedule WHERE schedule_id = ?', 
                      (data['schedule_id'],))
        slot = cursor.fetchone()
    
    await message.answer(
        f"✅ *Запись успешно создана!*\n\n"
        f"💇‍♀️ Услуга: {data['service_name']}\n"
        f"👨‍🎨 Мастер: {data['master_name']}\n"
        f"📅 Дата: {data['booking_date']}\n"
        f"⏰ Время: {slot['time_start']}\n"
        f"📞 Ваш телефон: {phone}\n\n"
        f"Я напомню о записи за день до визита.\n"
        f"Изменить или отменить запись можно через «Мои записи»",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    
    await state.clear()

@router.message(Command("mybookings"))
@router.message(F.text == "📋 Мои записи")
async def cmd_my_bookings(message: Message):
    """Показать записи клиента"""
    bookings = get_client_bookings(message.from_user.id)
    
    if not bookings:
        await message.answer(
            "📋 У вас пока нет активных записей.\n\n"
            "Чтобы записаться, нажмите «📅 Записаться»",
            reply_markup=get_main_keyboard()
        )
        return
    
    for booking in bookings:
        text = (
            f"📝 *Запись #{booking['booking_id']}*\n\n"
            f"💇‍♀️ Услуга: {booking['service_name']}\n"
            f"👨‍🎨 Мастер: {booking['master_name']}\n"
            f"💰 Стоимость: {booking['price']}₽\n"
            f"📅 Дата: {booking['booking_date']}\n"
            f"⏰ Время: {booking['booking_time']}\n"
            f"📊 Статус: {'✅ Подтверждена' if booking['status'] == 'confirmed' else '❌ Отменена'}\n"
        )
        
        if booking['status'] == 'confirmed':
            await message.answer(
                text,
                reply_markup=get_booking_actions_keyboard(booking['booking_id']),
                parse_mode="Markdown"
            )
        else:
            await message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data.startswith("cancel_"))
async def cancel_booking_callback(callback: CallbackQuery):
    """Отмена записи через инлайн-кнопку"""
    booking_id = int(callback.data.split("_")[1])
    client = get_client(callback.from_user.id)
    
    if cancel_booking(booking_id, client['client_id']):
        await callback.answer("✅ Запись отменена")
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ Запись отменена",
            reply_markup=None
        )
    else:
        await callback.answer("❌ Ошибка при отмене", show_alert=True)

@router.message(F.text == "ℹ️ О салоне")
async def cmd_about(message: Message):
    """Информация о салоне"""
    text = """
🏢 *О салоне красоты «Элеганс»*

Мы работаем с 2015 года и дарим красоту нашим гостям.

✨ *Наши преимущества:*
• Профессиональные мастера с опытом от 5 лет
• Современное оборудование и материалы
• Индивидуальный подход к каждому клиенту
• Уютная атмосфера и бесплатный кофе

⏰ *Режим работы:*
Ежедневно с 09:00 до 21:00

📍 *Адрес:*
г. Ижевск, ул. Пушкинская, 123

📞 *Телефон для справок:*
+7 (912) 123-45-67
    """
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📞 Контакты")
async def cmd_contacts(message: Message):
    """Контакты салона"""
    text = """
📞 *Наши контакты:*

📍 *Адрес:*
г. Ижевск, ул. Пушкинская, 123

📱 *Телефон:*
+7 (912) 123-45-67

📧 *Email:*
salon@elegance.ru

📱 *Социальные сети:*
Telegram: @elegance_salon
Instagram: @elegance_salon

🕐 *График работы:*
Пн-Вс: 09:00 - 21:00

*Как добраться:*
Остановка «Центральная», 5 минут пешком от ТЦ «Италмас»
    """
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "◀️ Клиентское меню")
async def back_to_client_menu(message: Message):
    """Возврат в клиентское меню"""
    await message.answer(
        "Возвращаемся в клиентское меню 👋",
        reply_markup=get_main_keyboard()
    )