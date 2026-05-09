import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import *
from keyboards import *
from utils import get_izhevsk_now, get_tomorrow_str

router = Router()
logger = logging.getLogger(__name__)

# Состояния FSM для записи
class BookingStates(StatesGroup):
    waiting_for_service = State()
    waiting_for_master = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_phone = State()

# ============ ОСНОВНЫЕ КОМАНДЫ ============

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    client = get_client(user.id)
    
    if not client:
        add_client(user.id, user.first_name)
        await message.answer(
            f"👋 Добро пожаловать в салон красоты «Бабочка», {user.first_name}!\n\n"
            f"💇‍♀️ Нажмите «Услуги», чтобы посмотреть цены\n"
            f"📅 «Записаться» — чтобы выбрать время\n"
            f"📋 «Мои записи» — чтобы посмотреть или отменить запись",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            f"С возвращением, {user.first_name}! 👋\nЧем могу помочь сегодня?",
            reply_markup=get_main_keyboard()
        )

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
📖 *Команды бота:*

/start — начать работу
/services — список услуг
/masters — список мастеров
/book — записаться на услугу
/mybookings — мои записи
/remindme — напоминания на завтра
/help — эта справка

📞 *Контакты салона:*
Телефон: +7 (912) 123-45-67
Адрес: г. Ижевск, ул. Пушкинская, 123
    """
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("services"))
@router.message(F.text == "💇‍♀️ Услуги")
async def cmd_services(message: Message):
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
    masters = get_active_masters()
    
    if not masters:
        await message.answer("😔 Мастера временно не добавлены")
        return
    
    text = "👨‍🎨 *Наши мастера:*\n\n"
    for master in masters:
        text += f"✨ *{master['name']}*\n"
        text += f"   Специализация: {master['specialization']}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("book"))
@router.message(F.text == "📅 Записаться")
async def cmd_book_start(message: Message, state: FSMContext):
    """Начать запись — показать услуги"""
    services = get_all_services()
    
    if not services:
        await message.answer("😔 Услуги временно недоступны")
        return
    
    await message.answer(
        "💇‍♀️ *Выберите услугу:*\n\nНажмите на нужную услугу",
        reply_markup=get_services_inline_keyboard(services),
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.waiting_for_service)
    logger.info(f"Пользователь {message.from_user.id} начал запись, состояние: waiting_for_service")

# ============ ОБРАБОТЧИКИ CALLBACK (КНОПОК) ============

@router.callback_query(F.data.startswith("service_"))
async def process_service_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора услуги"""
    try:
        service_id = int(callback.data.split("_")[1])
        service = get_service(service_id)
        
        if not service:
            await callback.answer("Услуга не найдена")
            return
        
        await state.update_data(service_id=service_id, service_name=service['name'], service_category=service['category'])
        
        # Получаем мастеров по категории услуги
        masters = get_masters_by_category(service['category'])
        
        if not masters:
            await callback.message.edit_text(
                f"😔 К сожалению, нет мастеров для услуги {service['name']}",
                reply_markup=None
            )
            await callback.answer()
            return
        
        await callback.message.edit_text(
            f"✅ Выбрана услуга: *{service['name']}*\n"
            f"💰 Цена: {service['price']}₽\n"
            f"⏱ Длительность: {service['duration_min']} мин\n\n"
            f"👨‍🎨 *Выберите мастера:*",
            reply_markup=get_masters_inline_keyboard(masters),
            parse_mode="Markdown"
        )
        await state.set_state(BookingStates.waiting_for_master)
        await callback.answer(f"Выбрана услуга: {service['name']}")
        logger.info(f"Пользователь выбрал услугу: {service['name']}")
    except Exception as e:
        logger.error(f"Ошибка в process_service_selection: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data.startswith("master_"))
async def process_master_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора мастера"""
    try:
        master_id = int(callback.data.split("_")[1])
        master = get_master(master_id)
        
        if not master:
            await callback.answer("Мастер не найден")
            return
        
        await state.update_data(master_id=master_id, master_name=master['name'])
        
        await callback.message.edit_text(
            f"✅ Выбран мастер: *{master['name']}*\n\n"
            f"📅 *Введите желаемую дату в формате ДД.ММ.ГГГГ*\n"
            f"Например: 25.05.2026\n\n"
            f"Доступны даты от сегодня до +14 дней",
            parse_mode="Markdown"
        )
        await state.set_state(BookingStates.waiting_for_date)
        await callback.answer(f"Выбран мастер: {master['name']}")
        logger.info(f"Пользователь выбрал мастера: {master['name']}")
    except Exception as e:
        logger.error(f"Ошибка в process_master_selection: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data.startswith("slot_"))
async def process_slot_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени"""
    try:
        schedule_id = int(callback.data.split("_")[1])
        await state.update_data(schedule_id=schedule_id)
        
        # Получаем информацию о времени
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT time_start FROM master_schedule WHERE schedule_id = ?', (schedule_id,))
            slot = cursor.fetchone()
        
        if slot:
            await state.update_data(booking_time=slot['time_start'])
        
        await callback.message.edit_text(
            f"✅ Время выбрано!\n\n"
            f"📱 *Укажите ваш номер телефона*\n"
            f"Пример: +7 (912) 123-45-67\n\n"
            f"Или нажмите «Отмена»",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(BookingStates.waiting_for_phone)
        await callback.answer("Время выбрано")
        logger.info(f"Пользователь выбрал слот {schedule_id}")
    except Exception as e:
        logger.error(f"Ошибка в process_slot_selection: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено")
    await callback.message.answer("Возврат в главное меню", reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору услуг"""
    services = get_all_services()
    await callback.message.edit_text(
        "💇‍♀️ *Выберите услугу:*",
        reply_markup=get_services_inline_keyboard(services),
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.waiting_for_service)
    await callback.answer()

@router.callback_query(F.data == "back_to_masters")
async def back_to_masters(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору мастера"""
    data = await state.get_data()
    service_id = data.get('service_id')
    
    if service_id:
        service = get_service(service_id)
        if service:
            masters = get_masters_by_category(service['category'])
            await callback.message.edit_text(
                f"✅ Выбрана услуга: *{service['name']}*\n\n"
                f"👨‍🎨 *Выберите мастера:*",
                reply_markup=get_masters_inline_keyboard(masters),
                parse_mode="Markdown"
            )
            await state.set_state(BookingStates.waiting_for_master)
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_booking_"))
async def cancel_booking_callback(callback: CallbackQuery):
    """Отмена записи"""
    try:
        booking_id = int(callback.data.split("_")[2])
        client = get_client(callback.from_user.id)
        
        if cancel_booking(booking_id, client['client_id']):
            await callback.answer("✅ Запись отменена")
            await callback.message.edit_text(
                callback.message.text + "\n\n❌ Запись отменена",
                reply_markup=None
            )
        else:
            await callback.answer("❌ Ошибка при отмене", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка отмены записи: {e}")
        await callback.answer("Ошибка", show_alert=True)

# ============ ОБРАБОТКА ТЕКСТОВЫХ ВВОДОВ ============

@router.message(BookingStates.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    """Обработка ввода даты"""
    date_str = message.text.strip()
    
    try:
        selected_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        today = get_izhevsk_now().date()
        
        if selected_date < today:
            await message.answer("❌ Нельзя выбрать прошедшую дату. Введите дату от сегодняшней")
            return
        
        if selected_date > today + timedelta(days=14):
            await message.answer("❌ Можно записаться только на 14 дней вперёд")
            return
        
    except ValueError:
        await message.answer("❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ\nНапример: 25.05.2026")
        return
    
    await state.update_data(booking_date=date_str)
    
    data = await state.get_data()
    free_slots = get_free_slots(data['master_id'], date_str)
    
    if not free_slots:
        await message.answer(
            f"😔 На {date_str} нет свободных слотов у мастера {data['master_name']}.\n"
            f"Пожалуйста, выберите другую дату через /book"
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

@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка ввода телефона и создание записи"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Запись отменена", reply_markup=get_main_keyboard())
        return
    
    phone = message.text.strip()
    data = await state.get_data()
    
    client = get_client(message.from_user.id)
    
    # Обновляем телефон клиента
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE clients SET phone = ? WHERE telegram_id = ?', 
                      (phone, message.from_user.id))
        conn.commit()
    
    # Создаём запись
    add_booking(
        client_id=client['client_id'],
        master_id=data['master_id'],
        service_id=data['service_id'],
        schedule_id=data['schedule_id'],
        date=data['booking_date'],
        time=data.get('booking_time', '')
    )
    
    await message.answer(
        f"✅ *Запись успешно создана!*\n\n"
        f"💇‍♀️ Услуга: {data['service_name']}\n"
        f"👨‍🎨 Мастер: {data['master_name']}\n"
        f"📅 Дата: {data['booking_date']}\n"
        f"⏰ Время: {data.get('booking_time', '')}\n"
        f"📞 Телефон: {phone}\n\n"
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
        )
        
        await message.answer(
            text,
            reply_markup=get_booking_actions_keyboard(booking['booking_id']),
            parse_mode="Markdown"
        )

@router.message(Command("remindme"))
async def cmd_remind_me(message: Message):
    """Напоминания на завтра"""
    tomorrow_str = get_tomorrow_str()
    
    bookings = get_client_bookings(message.from_user.id)
    tomorrow_bookings = [b for b in bookings if b['booking_date'] == tomorrow_str]
    
    if not tomorrow_bookings:
        await message.answer(
            "📭 У вас нет записей на завтра.\n\n"
            "Хотите записаться? Используйте команду /book",
            reply_markup=get_main_keyboard()
        )
        return
    
    text = f"📢 *Ваши записи на завтра ({tomorrow_str}):*\n\n"
    for b in tomorrow_bookings:
        text += f"💇‍♀️ {b['service_name']}\n"
        text += f"👨‍🎨 {b['master_name']}\n"
        text += f"⏰ {b['booking_time']}\n\n"
    text += "✨ Ждём вас в салоне!"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "ℹ️ О салоне")
async def cmd_about(message: Message):
    text = """
🏢 *О салоне красоты «Бабочка»*

✨ *Наши преимущества:*
• Профессиональные мастера с опытом от 5 лет
• Современное оборудование и материалы
• Уютная атмосфера и бесплатный кофе

⏰ *Режим работы:*
Ежедневно с 09:00 до 21:00

📍 *Адрес:*
г. Ижевск, ул. Пушкинская, 123
    """
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📞 Контакты")
async def cmd_contacts(message: Message):
    text = """
📞 *Наши контакты:*

📍 *Адрес:* г. Ижевск, ул. Пушкинская, 123

📱 *Телефон:* +7 (912) 123-45-67

📧 *Email:* salon@butterfly.ru

🕐 *График работы:* Пн-Вс: 09:00 - 21:00
    """
    await message.answer(text, parse_mode="Markdown")