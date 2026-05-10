import logging
import traceback
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot import bot

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
    waiting_for_name = State()
    waiting_for_phone = State()

# ============ ОСНОВНЫЕ КОМАНДЫ ============

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    client = get_client(user.id)
    
    if not client:
        add_client(user.id, user.first_name)
    
    # Проверяем, админ ли пользователь
    if is_admin(user.id):
        # Для админов показываем меню с кнопкой "👑 Админ панель"
        kb = [
            [KeyboardButton(text="💇‍♀️ Услуги"), KeyboardButton(text="👨‍🎨 Мастера")],
            [KeyboardButton(text="📅 Записаться"), KeyboardButton(text="📋 Мои записи")],
            [KeyboardButton(text="ℹ️ О салоне"), KeyboardButton(text="📞 Контакты")],
            [KeyboardButton(text="👑 Админ панель")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        
        await message.answer(
            f"👋 Добро пожаловать, *{user.first_name}*!\n\n"
            f"У вас есть права администратора. Нажмите «👑 Админ панель» для управления.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        # Обычное меню для клиентов
        await message.answer(
            f"👋 Добро пожаловать в салон красоты «Бабочка», {user.first_name}!",
            reply_markup=get_main_keyboard()
        )

@router.message(F.text == "👑 Админ панель")
async def admin_button_panel(message: Message):
    """Кнопка для открытия админ-панели (только для админов)"""
    if is_admin(message.from_user.id):
        await message.answer(
            "👑 *Панель администратора*\n\nВыберите действие:",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer("⛔ У вас нет прав администратора")

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
📖 *Команды бота:*

/start — начать работу
/services — список услуг и цен
/masters — список мастеров
/book — записаться на услугу
/mybookings — мои записи
/help — эта справка

📞 *Контакты салона:*
Телефон: +7 (912) 123-45-67
Адрес: г. Ижевск, ул. Пушкинская, 123
    """
    await message.answer(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

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
        text += f"   ⏱ ~{service['duration_min']} мин | 💰 {service['price']}₽\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("masters"))
@router.message(F.text == "👨‍🎨 Мастера")
async def cmd_masters(message: Message):
    masters = get_all_masters(include_inactive=False)
    
    if not masters:
        await message.answer("😔 Мастера временно не добавлены")
        return
    
    text = "👨‍🎨 *Наши мастера:*\n\n"
    for master in masters:
        # Преобразуем Row в словарь, если нужно
        if hasattr(master, 'keys'):
            master_dict = {key: master[key] for key in master.keys()}
        else:
            master_dict = dict(master)
        
        name = master_dict.get('name', 'Неизвестно')
        specialization = master_dict.get('specialization', 'не указана')
        experience = master_dict.get('experience', 'не указан')
        
        text += f"✨ *{name}*\n"
        text += f"   Специализация: {specialization}\n"
        text += f"   📆 Опыт: {experience}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("book"))
@router.message(F.text == "📅 Записаться")
async def cmd_book_start(message: Message, state: FSMContext):
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
    logger.info(f"Пользователь {message.from_user.id} начал запись")

# ============ ОБРАБОТЧИКИ CALLBACK ============

@router.callback_query(BookingStates.waiting_for_service, F.data.startswith("service_"))
async def process_service_selection(callback: CallbackQuery, state: FSMContext):
    try:
        service_id = int(callback.data.split("_")[1])
        service = get_service(service_id)
        
        if not service:
            await callback.answer("Услуга не найдена")
            return
        
        # Преобразуем в словарь для удобства
        if isinstance(service, dict):
            service_dict = service
        else:
            service_dict = dict(service)
        
        category = service_dict.get('category', 'hair')
        
        await state.update_data(
            service_id=service_id, 
            service_name=service_dict['name'], 
            service_category=category
        )
        
        masters = get_masters_by_category(category)
        
        if not masters:
            await callback.message.edit_text(
                f"😔 К сожалению, нет мастеров для услуги {service_dict['name']}",
                reply_markup=None
            )
            await callback.answer()
            return
        
        await callback.message.edit_text(
            f"✅ Выбрана услуга: *{service_dict['name']}*\n"
            f"💰 Цена: {service_dict['price']}₽\n"
            f"⏱ Длительность: ~{service_dict['duration_min']} мин\n\n"
            f"👨‍🎨 *Выберите мастера:*",
            reply_markup=get_masters_inline_keyboard(masters),
            parse_mode="Markdown"
        )
        await state.set_state(BookingStates.waiting_for_master)
        await callback.answer(f"✅ Выбрана услуга: {service_dict['name']}")
        
    except Exception as e:
        logger.error(f"Ошибка в process_service_selection: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.callback_query(BookingStates.waiting_for_master, F.data.startswith("master_"))
async def process_master_selection(callback: CallbackQuery, state: FSMContext):
    try:
        master_id = int(callback.data.split("_")[1])
        master = get_master(master_id)
        
        if not master:
            await callback.answer("Мастер не найден")
            return
        
        # Преобразуем в словарь
        if hasattr(master, 'keys'):
            master_dict = {key: master[key] for key in master.keys()}
        else:
            master_dict = dict(master)
        
        await state.update_data(master_id=master_id, master_name=master_dict['name'])
        
        await callback.message.edit_text(
            f"✅ Выбран мастер: *{master_dict['name']}*\n\n"
            f"📅 *Введите желаемую дату в формате ДД.ММ.ГГГГ*\n"
            f"Например: 25.05.2026\n\n"
            f"Доступны даты от сегодня до +14 дней",
            parse_mode="Markdown"
        )
        await state.set_state(BookingStates.waiting_for_date)
        await callback.answer(f"✅ Выбран мастер: {master_dict['name']}")
        
    except Exception as e:
        logger.error(f"Ошибка в process_master_selection: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.callback_query(BookingStates.waiting_for_time, F.data.startswith("slot_"))
async def process_slot_selection(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split("_")
        if len(parts) < 2:
            await callback.answer("❌ Ошибка: неверный формат данных")
            return
        
        schedule_id = int(parts[1])
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT schedule_id, time_start, time_end FROM master_schedule WHERE schedule_id = ?', (schedule_id,))
            slot = cursor.fetchone()
        
        if not slot:
            await callback.answer("❌ Слот не найден", show_alert=True)
            return
        
        await state.update_data(schedule_id=schedule_id, booking_time=slot['time_start'])
        
        await callback.message.delete()
        
        await callback.message.answer(
            f"✅ Время выбрано: *{slot['time_start']}*\n\n"
            f"📝 *Как вас зовут?*\n"
            f"(Напишите ваше имя, пожалуйста)\n\n"
            f"Пример: Анна\n\n"
            f"Или нажмите «Отмена»",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(BookingStates.waiting_for_name)
        await callback.answer(f"✅ Выбрано время: {slot['time_start']}")
        logger.info(f"Пользователь выбрал слот {schedule_id}, время {slot['time_start']}")
        
    except Exception as e:
        logger.error(f"Ошибка в process_slot_selection: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Запись отменена", reply_markup=get_main_keyboard())
        return
    
    name = message.text.strip()
    await state.update_data(client_name=name)
    
    await message.answer(
        f"✅ Спасибо, {name}!\n\n"
        f"📱 *Укажите ваш номер телефона*\n"
        f"Пример: +7 (912) 123-45-67\n\n"
        f"Или нажмите «Отмена»",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.waiting_for_phone)

@router.message(BookingStates.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
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
    master_id = data.get('master_id')
    master_name = data.get('master_name')
    
    if not master_id:
        await message.answer("❌ Ошибка: мастер не выбран. Начните запись заново: /book")
        await state.clear()
        return
    
    free_slots = get_free_slots(master_id, date_str)
    
    if not free_slots or len(free_slots) == 0:
        await message.answer(
            f"😔 На {date_str} нет свободных слотов у мастера {master_name}.\n\n"
            f"Пожалуйста, выберите другую дату через команду /book",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return
    
    slots_keyboard = get_slots_inline_keyboard(free_slots)
    if not slots_keyboard:
        await message.answer("❌ Ошибка формирования клавиатуры с временем")
        return
    
    await message.answer(
        f"📅 Дата: {date_str}\n\n"
        f"⏰ *Выберите удобное время:*",
        reply_markup=slots_keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.waiting_for_time)
    logger.info(f"Пользователь выбрал дату {date_str}, найдено слотов: {len(free_slots)}")

@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка ввода телефона и создание записи с уведомлением админов"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Запись отменена", reply_markup=get_main_keyboard())
        return
    
    phone = message.text.strip()
    
    if not phone:
        await message.answer("❌ Введите номер телефона или нажмите «Отмена»")
        return
    
    data = await state.get_data()
    
    required_fields = ['master_id', 'service_id', 'schedule_id', 'booking_date', 'booking_time', 'client_name']
    for field in required_fields:
        if field not in data:
            await message.answer(f"❌ Ошибка: не хватает данных. Начните запись заново: /book")
            await state.clear()
            return
    
    client = get_client(message.from_user.id)
    client_name = data.get('client_name', message.from_user.first_name)
    
    if not client:
        add_client(message.from_user.id, client_name, phone)
        client = get_client(message.from_user.id)
    else:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE clients SET name = ?, phone = ? WHERE telegram_id = ?', 
                          (client_name, phone, message.from_user.id))
            conn.commit()
    
    # Получаем реальную длительность услуги
    service = get_service(data['service_id'])
    if not service:
        await message.answer("❌ Услуга не найдена")
        await state.clear()
        return
    
    duration_min = service['duration_min']
    master_name = data.get('master_name', 'Не указан')
    service_name = data.get('service_name', 'Не указана')
    booking_date = data['booking_date']
    booking_time = data['booking_time']
    
    try:
        booking_id = add_booking_with_duration(
            client_id=client['client_id'],
            master_id=data['master_id'],
            service_id=data['service_id'],
            schedule_id=data['schedule_id'],
            date=booking_date,
            time=booking_time,
            duration_min=duration_min
        )
        
        if not booking_id:
            await message.answer(
                "❌ К сожалению, выбранное время уже недоступно.\n"
                "Пожалуйста, выберите другое время через /book",
                reply_markup=get_main_keyboard()
            )
            await state.clear()
            return
        
        # Отправляем подтверждение клиенту
        await message.answer(
            f"✅ *Запись успешно создана!*\n\n"
            f"👤 Имя: {client_name}\n"
            f"💇‍♀️ Услуга: {service_name}\n"
            f"👨‍🎨 Мастер: {master_name}\n"
            f"📅 Дата: {booking_date}\n"
            f"⏰ Время: {booking_time}\n"
            f"⏱ Длительность: ~{duration_min} мин\n"
            f"📞 Телефон: {phone}\n\n"
            f"✨ Я напомню о записи за день до визита.\n"
            f"Изменить или отменить запись можно через «Мои записи»",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
        # ============ УВЕДОМЛЕНИЕ ВСЕМ АДМИНИСТРАТОРАМ ============
        admins = get_all_admins()
        from bot import bot  # импортируем bot для отправки сообщений
        
        for admin in admins:
            try:
                await bot.send_message(
                    chat_id=admin['telegram_id'],
                    text=f"📢 *Новая запись!*\n\n"
                         f"👤 Клиент: {client_name}\n"
                         f"📞 Телефон: {phone}\n"
                         f"💇‍♀️ Услуга: {service_name}\n"
                         f"👨‍🎨 Мастер: {master_name}\n"
                         f"📅 Дата: {booking_date}\n"
                         f"⏰ Время: {booking_time}\n"
                         f"⏱ Длительность: ~{duration_min} мин",
                    parse_mode="Markdown"
                )
                logger.info(f"Уведомление отправлено админу {admin['telegram_id']}")
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin['telegram_id']}: {e}")
        
        logger.info(f"Создана запись #{booking_id} для клиента {message.from_user.id} ({client_name}), длительность {duration_min} мин")
        
    except Exception as e:
        logger.error(f"Ошибка при создании записи: {e}")
        await message.answer("❌ Ошибка при создании записи. Попробуйте позже.")
    
    await state.clear()

@router.message(Command("mybookings"))
@router.message(F.text == "📋 Мои записи")
async def cmd_my_bookings(message: Message):
    bookings = get_client_bookings(message.from_user.id)
    
    if not bookings:
        await message.answer(
            "📋 У вас пока нет активных записей.\n\nЧтобы записаться, нажмите «📅 Записаться»",
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

@router.callback_query(F.data.startswith("cancel_booking_"))
async def cancel_booking_callback(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("❌ Ошибка: неверный формат")
            return
        
        booking_id = int(parts[2])
        client = get_client(callback.from_user.id)
        
        if not client:
            await callback.answer("❌ Пользователь не найден")
            return
        
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
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.message(Command("remindme"))
async def cmd_remind_me(message: Message):
    tomorrow_str = get_tomorrow_str()
    
    bookings = get_client_bookings(message.from_user.id)
    tomorrow_bookings = [b for b in bookings if b['booking_date'] == tomorrow_str]
    
    if not tomorrow_bookings:
        await message.answer(
            "📭 У вас нет записей на завтра.\n\nХотите записаться? Используйте команду /book",
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

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("👑 *Панель администратора*\n\nВыберите действие:", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    else:
        await message.answer("⛔ У вас нет прав администратора")

# ============ КНОПКИ "НАЗАД" И "ОТМЕНА" ============

@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено")
    await callback.message.answer("Возврат в главное меню", reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext):
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
    data = await state.get_data()
    service_id = data.get('service_id')
    
    if service_id:
        service = get_service(service_id)
        if service:
            category = service.get('category', 'hair')
            masters = get_masters_by_category(category)
            await callback.message.edit_text(
                f"✅ Выбрана услуга: *{service['name']}*\n\n"
                f"👨‍🎨 *Выберите мастера:*",
                reply_markup=get_masters_inline_keyboard(masters),
                parse_mode="Markdown"
            )
            await state.set_state(BookingStates.waiting_for_master)
    await callback.answer()