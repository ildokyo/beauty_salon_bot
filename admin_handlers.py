import logging
import math
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import *
from keyboards import *

router = Router()
logger = logging.getLogger(__name__)

# Состояния
class AddMasterStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_specialization = State()
    waiting_for_experience = State()
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

class DeleteMasterStates(StatesGroup):
    waiting_for_master_id = State()

class RestoreMasterStates(StatesGroup):
    waiting_for_master_id = State()

class DeleteServiceStates(StatesGroup):
    waiting_for_service_id = State()

class RestoreServiceStates(StatesGroup):
    waiting_for_service_id = State()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()

class AdminBookingStates(StatesGroup):
    waiting_for_client_phone = State() 
    waiting_for_name = State() 
    waiting_for_service = State()
    waiting_for_master = State()
    waiting_for_date = State()
    waiting_for_time = State()

# ============ АДМИН ПАНЕЛЬ ============

@router.message(Command("admin"))
async def cmd_admin_panel(message: Message):
    if is_admin(message.from_user.id):
        await message.answer(
            "👑 *Панель администратора*\n\nВыберите действие:",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer("🔐 У вас нет прав администратора", reply_markup=get_main_keyboard())

@router.message(Command("becomeadmin"))
async def cmd_become_admin(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Используйте: /becomeadmin КОД\n\nКод: SALON2026")
        return
    
    code = parts[1]
    ADMIN_SECRET_CODE = "SALON2026"
    
    if code == ADMIN_SECRET_CODE:
        add_admin(message.from_user.id)
        
        # Отправляем сообщение об успехе
        await message.answer(
            "✅ *Вы стали администратором!*\n\n"
            "Открываю панель управления...",
            parse_mode="Markdown"
        )
        
        # АВТОМАТИЧЕСКИ ПОКАЗЫВАЕМ АДМИН-ПАНЕЛЬ (без команды /admin)
        await message.answer(
            "👑 *Панель администратора*\n\nВыберите действие:",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Неверный код доступа")

@router.message(F.text == "🚪 Выйти из админки")
async def cmd_exit_admin(message: Message):
    await message.answer("👋 Вы вышли из панели администратора", reply_markup=get_main_keyboard())

@router.message(F.text == "◀️ Клиентское меню")
async def back_to_client_menu(message: Message):
    await message.answer("Возвращаемся в клиентское меню 👋", reply_markup=get_main_keyboard())

@router.message(F.text == "🔙 Назад в админку")
async def back_to_admin(message: Message):
    await message.answer("Возврат в панель администратора", reply_markup=get_admin_keyboard())

# ============ РАССЫЛКА ============

@router.message(F.text == "📢 Рассылка")
async def cmd_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer(
        "📢 *Рассылка сообщений*\n\n"
        "Введите текст, который хотите отправить ВСЕМ клиентам:\n\n"
        "Или нажмите «Отмена»",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(BroadcastStates.waiting_for_message)

@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Рассылка отменена", reply_markup=get_admin_keyboard())
        return
    
    text = message.text
    clients = get_all_clients()
    
    if not clients:
        await message.answer("📭 Нет клиентов для рассылки")
        await state.clear()
        return
    
    success = 0
    fail = 0
    
    await message.answer(f"🔄 Начинаю рассылку {len(clients)} клиентам...")
    
    for client in clients:
        try:
            await message.bot.send_message(
                chat_id=client['telegram_id'],
                text=f"📢 *Сообщение от администрации*\n\n{text}",
                parse_mode="Markdown"
            )
            success += 1
        except:
            fail += 1
    
    await message.answer(
        f"✅ Рассылка завершена!\n"
        f"📨 Отправлено: {success}\n"
        f"❌ Ошибок: {fail}",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

# ============ ЗАПИСЬ КЛИЕНТА ЧЕРЕЗ АДМИНА ============

@router.message(F.text == "📝 Записать клиента")
async def cmd_admin_booking(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer(
        "📝 *Запись клиента через администратора*\n\n"
        "Введите **номер телефона** клиента (в формате +7XXXXXXXXXX):\n\n"
        "Пример: +79123456789\n\n"
        "Или нажмите «Отмена»",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminBookingStates.waiting_for_client_phone)

@router.message(AdminBookingStates.waiting_for_client_phone)
async def admin_booking_client(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Запись отменена", reply_markup=get_admin_keyboard())
        return
    
    phone = message.text.strip()
    
    # Проверяем формат телефона
    if not phone.startswith('+') or len(phone) < 11:
        await message.answer(
            "❌ Неверный формат телефона. Используйте формат: +7XXXXXXXXXX\n\n"
            "Пример: +79123456789",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Ищем клиента по номеру телефона
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE phone = ?', (phone,))
        client = cursor.fetchone()
    
    if client:
        await state.update_data(client_id=client['client_id'], client_name=client['name'])
        await message.answer(f"✅ Найден клиент: *{client['name']}*", parse_mode="Markdown")
        
        # Продолжаем выбор услуги
        services = get_all_services()
        if not services:
            await message.answer("😔 Услуги временно недоступны")
            await state.clear()
            return
        
        await message.answer(
            "💇‍♀️ *Выберите услугу:*",
            reply_markup=get_services_inline_keyboard(services),
            parse_mode="Markdown"
        )
        await state.set_state(AdminBookingStates.waiting_for_service)
    else:
        await state.update_data(client_phone=phone)
        await message.answer(
            f"📝 Клиент с номером *{phone}* не найден в базе.\n\n"
            f"Введите **ИМЯ** клиента для создания новой записи:\n\n"
            f"Пример: Анна",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(AdminBookingStates.waiting_for_name)

@router.message(AdminBookingStates.waiting_for_name)
async def admin_booking_new_client_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Запись отменена", reply_markup=get_admin_keyboard())
        return
    
    name = message.text.strip()
    
    if not name or len(name) < 2:
        await message.answer("❌ Введите корректное имя (минимум 2 буквы)", reply_markup=get_cancel_keyboard())
        return
    
    data = await state.get_data()
    client_phone = data.get('client_phone')
    
    if not client_phone:
        await message.answer("❌ Ошибка: номер телефона не найден. Начните заново.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    # Создаём нового клиента (telegram_id не указываем — будет NULL)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO clients (name, phone) VALUES (?, ?)', (name, client_phone))
        client_id = cursor.lastrowid
        conn.commit()
    
    await state.update_data(client_id=client_id, client_name=name)
    
    await message.answer(f"✅ Создан новый клиент: *{name}* (тел: {client_phone})", parse_mode="Markdown")
    
    services = get_all_services()
    if not services:
        await message.answer("😔 Услуги временно недоступны")
        await state.clear()
        return
    
    await message.answer(
        "💇‍♀️ *Выберите услугу:*",
        reply_markup=get_services_inline_keyboard(services),
        parse_mode="Markdown"
    )
    await state.set_state(AdminBookingStates.waiting_for_service)

@router.callback_query(AdminBookingStates.waiting_for_service, F.data.startswith("service_"))
async def admin_booking_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    service = get_service(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена")
        return
    
    # Преобразуем в словарь
    if hasattr(service, 'keys'):
        service_dict = {key: service[key] for key in service.keys()}
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
            f"😔 Нет мастеров для услуги {service_dict['name']}",
            reply_markup=None
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"✅ Услуга: *{service_dict['name']}*\n"
        f"💰 Цена: {service_dict['price']}₽\n"
        f"⏱ Длительность: ~{service_dict['duration_min']} мин\n\n"
        f"👨‍🎨 *Выберите мастера:*",
        reply_markup=get_masters_inline_keyboard(masters),
        parse_mode="Markdown"
    )
    await state.set_state(AdminBookingStates.waiting_for_master)
    await callback.answer()

@router.callback_query(AdminBookingStates.waiting_for_master, F.data.startswith("master_"))
async def admin_booking_master(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[1])
    master = get_master(master_id)
    
    # Преобразуем в словарь
    if hasattr(master, 'keys'):
        master_dict = {key: master[key] for key in master.keys()}
    else:
        master_dict = dict(master)
    
    await state.update_data(master_id=master_id, master_name=master_dict['name'])
    
    await callback.message.edit_text(
        f"✅ Мастер: *{master_dict['name']}*\n\n"
        f"📅 *Введите дату в формате ДД.ММ.ГГГГ*\n"
        f"Например: 25.05.2026",
        parse_mode="Markdown"
    )
    await state.set_state(AdminBookingStates.waiting_for_date)
    await callback.answer()

@router.message(AdminBookingStates.waiting_for_date)
async def admin_booking_date(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Запись отменена", reply_markup=get_admin_keyboard())
        return
    
    date_str = message.text.strip()
    
    # Проверяем формат даты
    try:
        selected_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        today = get_izhevsk_now().date()
        
        if selected_date < today:
            await message.answer("❌ Нельзя выбрать прошедшую дату", reply_markup=get_cancel_keyboard())
            return
        
        if selected_date > today + timedelta(days=30):
            await message.answer("❌ Нельзя выбрать дату дальше 30 дней", reply_markup=get_cancel_keyboard())
            return
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ", reply_markup=get_cancel_keyboard())
        return
    
    await state.update_data(booking_date=date_str)
    
    data = await state.get_data()
    free_slots = get_free_slots(data['master_id'], date_str)
    
    if not free_slots:
        await message.answer(
            f"😔 На {date_str} нет свободных слотов у мастера {data['master_name']}.\n\n"
            f"Выберите другую дату:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await message.answer(
        f"📅 Дата: {date_str}\n\n"
        f"⏰ *Выберите время:*",
        reply_markup=get_slots_inline_keyboard(free_slots),
        parse_mode="Markdown"
    )
    await state.set_state(AdminBookingStates.waiting_for_time)

@router.callback_query(AdminBookingStates.waiting_for_time, F.data.startswith("slot_"))
async def admin_booking_time(callback: CallbackQuery, state: FSMContext):
    schedule_id = int(callback.data.split("_")[1])
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT time_start, time_end FROM master_schedule WHERE schedule_id = ?', (schedule_id,))
        slot = cursor.fetchone()
    
    if not slot:
        await callback.answer("❌ Слот не найден", show_alert=True)
        return
    
    data = await state.get_data()
    
    # Создаём запись
    booking_id = add_booking_with_duration(
        client_id=data['client_id'],
        master_id=data['master_id'],
        service_id=data['service_id'],
        schedule_id=schedule_id,
        date=data['booking_date'],
        time=slot['time_start'],
        duration_min=60  # будет заменено на реальную длительность в add_booking_with_duration
    )
    
    client_name = data.get('client_name', 'Клиент')
    
    await callback.message.delete()
    await callback.message.answer(
        f"✅ *Запись создана администратором!*\n\n"
        f"👤 Клиент: {client_name}\n"
        f"💇‍♀️ Услуга: {data['service_name']}\n"
        f"👨‍🎨 Мастер: {data['master_name']}\n"
        f"📅 Дата: {data['booking_date']}\n"
        f"⏰ Время: {slot['time_start']}\n\n"
        f"Клиент уведомлён о записи (если есть Telegram).",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer()

# ============ УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ ============

@router.message(F.text == "👥 Управление админами")
async def cmd_manage_admins(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer(
        "👥 *Управление администраторами*\n\nВыберите действие:",
        reply_markup=get_admin_management_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "➕ Добавить админа")
async def cmd_add_admin_prompt(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer(
        "📝 Введите Telegram ID нового администратора\n\nКак узнать ID: @userinfobot",
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
        await message.answer("❌ Неверный ID. Введите число.")

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
        await message.answer("❌ Неверный ID. Введите число.")

@router.message(F.text == "📋 Список админов")
async def cmd_list_admins(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    admins = get_all_admins_with_names()
    
    if not admins:
        await message.answer("📭 Нет администраторов")
        return
    
    text = "👥 *Список администраторов:*\n\n"
    for admin in admins:
        name = admin['name'] if admin['name'] else "Неизвестно"
        text += f"• {name} — `{admin['telegram_id']}`\n"
    
    await message.answer(text, parse_mode="Markdown")

# ============ УПРАВЛЕНИЕ МАСТЕРАМИ ============

@router.message(F.text == "👨‍🎨 Управление мастерами")
async def cmd_manage_masters(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer(
        "👨‍🎨 *Управление мастерами*\n\nВыберите действие:",
        reply_markup=get_masters_management_keyboard(),
        parse_mode="Markdown"
    )

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
    await message.answer("📆 Введите опыт работы (например: 5 лет):")
    await state.set_state(AddMasterStates.waiting_for_experience)

@router.message(AddMasterStates.waiting_for_experience)
async def add_master_experience(message: Message, state: FSMContext):
    await state.update_data(experience=message.text)
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
    add_master(data['name'], data['specialization'], data['experience'], category)
    
    await message.answer(
        f"✅ Мастер {data['name']} добавлен!\n"
        f"Специализация: {data['specialization']}\n"
        f"Опыт: {data['experience']}\n"
        f"Категория: {category}",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@router.message(F.text == "🗑 Удалить мастера")
async def cmd_delete_master_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    masters = get_all_masters(include_inactive=False)
    
    if not masters:
        await message.answer("📭 Нет активных мастеров для удаления")
        return
    
    text = "🗑 *Удаление мастера*\n\nСписок активных мастеров:\n"
    for master in masters:
        text += f"ID: {master['master_id']} — {master['name']} ({master['specialization']})\n"
    
    text += "\nВведите ID мастера для удаления:"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_cancel_keyboard())
    await state.set_state(DeleteMasterStates.waiting_for_master_id)

@router.message(DeleteMasterStates.waiting_for_master_id)
async def process_delete_master(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Удаление отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        master_id = int(message.text.strip())
        master = get_master(master_id)
        
        if not master:
            await message.answer(f"❌ Мастер с ID {master_id} не найден")
            await state.clear()
            return
        
        if master['is_active'] == 0:
            await message.answer(f"❌ Мастер {master['name']} уже удалён")
            await state.clear()
            return
        
        if delete_master(master_id):
            await message.answer(
                f"✅ Мастер {master['name']} (ID: {master_id}) скрыт!",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer(f"❌ Ошибка при удалении")
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите ID мастера (число)", reply_markup=get_cancel_keyboard())

@router.message(F.text == "🔄 Восстановить мастера")
async def cmd_restore_master_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    masters = get_all_masters(include_inactive=True)
    inactive_masters = [m for m in masters if m['is_active'] == 0]
    
    if not inactive_masters:
        await message.answer("📭 Нет скрытых мастеров для восстановления")
        return
    
    text = "🔄 *Восстановление мастера*\n\nСписок скрытых мастеров:\n"
    for master in inactive_masters:
        text += f"ID: {master['master_id']} — {master['name']} ({master['specialization']})\n"
    
    text += "\nВведите ID мастера для восстановления:"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_cancel_keyboard())
    await state.set_state(RestoreMasterStates.waiting_for_master_id)

@router.message(RestoreMasterStates.waiting_for_master_id)
async def process_restore_master(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Восстановление отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        master_id = int(message.text.strip())
        master = get_master(master_id)
        
        if not master:
            await message.answer(f"❌ Мастер с ID {master_id} не найден")
            await state.clear()
            return
        
        if master['is_active'] == 1:
            await message.answer(f"❌ Мастер {master['name']} уже активен")
            await state.clear()
            return
        
        if restore_master(master_id):
            await message.answer(
                f"✅ Мастер {master['name']} (ID: {master_id}) восстановлен!",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer(f"❌ Ошибка при восстановлении")
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите ID мастера (число)", reply_markup=get_cancel_keyboard())

@router.message(F.text == "📋 Список мастеров")
async def cmd_list_masters_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    masters = get_all_masters(include_inactive=True)
    
    if not masters:
        await message.answer("📭 Нет мастеров")
        return
    
    text = "👨‍🎨 *Список всех мастеров:*\n\n"
    for master in masters:
        # Преобразуем в словарь
        if hasattr(master, 'keys'):
            master_dict = {key: master[key] for key in master.keys()}
        else:
            master_dict = dict(master)
        
        status = "✅ Активен" if master_dict.get('is_active') == 1 else "❌ Скрыт"
        exp = master_dict.get('experience', 'не указан')
        text += f"ID: {master_dict.get('master_id')} — {master_dict.get('name')}\n"
        text += f"   Специализация: {master_dict.get('specialization')}\n"
        text += f"   Опыт: {exp}\n"
        text += f"   Статус: {status}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

# ============ УПРАВЛЕНИЕ УСЛУГАМИ ============

@router.message(F.text == "💇‍♀️ Управление услугами")
async def cmd_manage_services(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer(
        "💇‍♀️ *Управление услугами*\n\nВыберите действие:",
        reply_markup=get_services_management_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "➕ Добавить услугу")
async def cmd_add_service(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    await message.answer("💇‍♀️ Введите название услуги (со смайликом):", reply_markup=get_cancel_keyboard())
    await state.set_state(AddServiceStates.waiting_for_name)

@router.message(AddServiceStates.waiting_for_name)
async def add_service_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление отменено", reply_markup=get_admin_keyboard())
        return
    
    await state.update_data(name=message.text)
    await message.answer("⏱ Введите длительность в минутах (например: 60):")
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
        f"⏱ ~{data['duration']} мин\n"
        f"💰 {data['price']}₽",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@router.message(F.text == "🗑 Удалить услугу")
async def cmd_delete_service_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    services = get_all_services()
    
    if not services:
        await message.answer("📭 Нет активных услуг для удаления")
        return
    
    text = "🗑 *Удаление услуги*\n\nСписок активных услуг:\n"
    for service in services:
        text += f"ID: {service['service_id']} — {service['name']} — {service['price']}₽\n"
    
    text += "\nВведите ID услуги для удаления:"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_cancel_keyboard())
    await state.set_state(DeleteServiceStates.waiting_for_service_id)

@router.message(DeleteServiceStates.waiting_for_service_id)
async def process_delete_service(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Удаление отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        service_id = int(message.text.strip())
        service = get_service(service_id)
        
        if not service:
            await message.answer(f"❌ Услуга с ID {service_id} не найдена")
            await state.clear()
            return
        
        if service['is_active'] == 0:
            await message.answer(f"❌ Услуга {service['name']} уже удалена")
            await state.clear()
            return
        
        if delete_service(service_id):
            await message.answer(
                f"✅ Услуга {service['name']} (ID: {service_id}) скрыта!",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer(f"❌ Ошибка при удалении")
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите ID услуги (число)", reply_markup=get_cancel_keyboard())

@router.message(F.text == "🔄 Восстановить услугу")
async def cmd_restore_service_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    services = get_all_services_with_inactive()
    inactive_services = [s for s in services if s['is_active'] == 0]
    
    if not inactive_services:
        await message.answer("📭 Нет скрытых услуг для восстановления")
        return
    
    text = "🔄 *Восстановление услуги*\n\nСписок скрытых услуг:\n"
    for service in inactive_services:
        text += f"ID: {service['service_id']} — {service['name']} — {service['price']}₽\n"
    
    text += "\nВведите ID услуги для восстановления:"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_cancel_keyboard())
    await state.set_state(RestoreServiceStates.waiting_for_service_id)

@router.message(RestoreServiceStates.waiting_for_service_id)
async def process_restore_service(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Восстановление отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        service_id = int(message.text.strip())
        service = get_service(service_id)
        
        if not service:
            await message.answer(f"❌ Услуга с ID {service_id} не найдена")
            await state.clear()
            return
        
        if service['is_active'] == 1:
            await message.answer(f"❌ Услуга {service['name']} уже активна")
            await state.clear()
            return
        
        if restore_service(service_id):
            await message.answer(
                f"✅ Услуга {service['name']} (ID: {service_id}) восстановлена!",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer(f"❌ Ошибка при восстановлении")
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите ID услуги (число)", reply_markup=get_cancel_keyboard())

@router.message(F.text == "📋 Список услуг")
async def cmd_list_services_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    services = get_all_services_with_inactive()
    
    if not services:
        await message.answer("📭 Нет услуг")
        return
    
    text = "💇‍♀️ *Список всех услуг:*\n\n"
    for service in services:
        status = "✅ Активна" if service['is_active'] == 1 else "❌ Скрыта"
        text += f"ID: {service['service_id']} — {service['name']}\n"
        text += f"   ⏱ ~{service['duration_min']} мин | 💰 {service['price']}₽\n"
        text += f"   Статус: {status}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

# ============ ДОБАВЛЕНИЕ РАСПИСАНИЯ ============

@router.message(F.text == "📅 Добавить расписание")
async def cmd_add_schedule(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    masters = get_all_masters(include_inactive=False)
    text = "👨‍🎨 *Выберите мастера (введите ID):*\n\n"
    for master in masters:
        text += f"ID: {master['master_id']} — {master['name']} ({master['specialization']})\n"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_cancel_keyboard())
    await state.set_state(AddScheduleStates.waiting_for_master)

@router.message(AddScheduleStates.waiting_for_master)
async def add_schedule_master(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление расписания отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        master_id = int(message.text)
        await state.update_data(master_id=master_id)
        await message.answer("📅 Введите дату в формате ДД.ММ.ГГГГ (например: 25.05.2026):", reply_markup=get_cancel_keyboard())
        await state.set_state(AddScheduleStates.waiting_for_date)
    except ValueError:
        await message.answer("❌ Введите ID мастера (число)", reply_markup=get_cancel_keyboard())

@router.message(AddScheduleStates.waiting_for_date)
async def add_schedule_date(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление расписания отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(date=message.text)
        await message.answer("⏰ Введите время начала в формате ЧЧ:ММ (например: 10:00):", reply_markup=get_cancel_keyboard())
        await state.set_state(AddScheduleStates.waiting_for_start_time)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ", reply_markup=get_cancel_keyboard())

@router.message(AddScheduleStates.waiting_for_start_time)
async def add_schedule_start(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление расписания отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        datetime.strptime(message.text, "%H:%M")
        await state.update_data(start_time=message.text)
        await message.answer("⏰ Введите время окончания в формате ЧЧ:ММ (например: 18:00):", reply_markup=get_cancel_keyboard())
        await state.set_state(AddScheduleStates.waiting_for_end_time)
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ", reply_markup=get_cancel_keyboard())

@router.message(AddScheduleStates.waiting_for_end_time)
async def add_schedule_end(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление расписания отменено", reply_markup=get_admin_keyboard())
        return
    
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
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ", reply_markup=get_cancel_keyboard())

# ============ ПРОСМОТР ВСЕХ ЗАПИСЕЙ ============

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
# ============ ДОБАВЛЕНИЕ РАСПИСАНИЯ (ГЕНЕРАЦИЯ НА ПЕРИОД) ============

class GenerateScheduleStates(StatesGroup):
    waiting_for_master = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()

@router.message(F.text == "📅 Добавить расписание")
async def cmd_generate_schedule(message: Message, state: FSMContext):
    """Генерация расписания на период (вместо ручного добавления)"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступно только администраторам")
        return
    
    masters = get_all_masters(include_inactive=False)
    
    if not masters:
        await message.answer("📭 Нет мастеров для добавления расписания")
        return
    
    text = "👨‍🎨 *Выберите мастера (введите ID):*\n\n"
    for master in masters:
        text += f"ID: {master['master_id']} — {master['name']} ({master['specialization']})\n"
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_cancel_keyboard())
    await state.set_state(GenerateScheduleStates.waiting_for_master)

@router.message(GenerateScheduleStates.waiting_for_master)
async def generate_schedule_master(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление расписания отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        master_id = int(message.text.strip())
        master = get_master(master_id)
        if not master:
            await message.answer(f"❌ Мастер с ID {master_id} не найден", reply_markup=get_cancel_keyboard())
            return
        
        await state.update_data(master_id=master_id, master_name=master['name'])
        await message.answer(
            "📅 *Шаг 2 из 4*\n\n"
            "Введите **дату начала** в формате ДД.ММ.ГГГГ:\n"
            "Например: 10.05.2026",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(GenerateScheduleStates.waiting_for_start_date)
    except ValueError:
        await message.answer("❌ Введите ID мастера (число)", reply_markup=get_cancel_keyboard())

@router.message(GenerateScheduleStates.waiting_for_start_date)
async def generate_schedule_start_date(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление расписания отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(start_date=message.text)
        await message.answer(
            "📅 *Шаг 3 из 4*\n\n"
            "Введите **дату окончания** в формате ДД.ММ.ГГГГ:\n"
            "Например: 20.05.2026\n\n"
            "✅ Расписание будет создано на ВСЕ дни в этом диапазоне "
            "(включая выходные)",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(GenerateScheduleStates.waiting_for_end_date)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ", reply_markup=get_cancel_keyboard())

@router.message(GenerateScheduleStates.waiting_for_end_date)
async def generate_schedule_end_date(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление расписания отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        end_date = datetime.strptime(message.text, "%d.%m.%Y")
        data = await state.get_data()
        start_date = datetime.strptime(data['start_date'], "%d.%m.%Y")
        
        if end_date < start_date:
            await message.answer("❌ Дата окончания не может быть раньше даты начала", reply_markup=get_cancel_keyboard())
            return
        
        await state.update_data(end_date=message.text)
        await message.answer(
            "⏰ *Шаг 4 из 4*\n\n"
            "Введите **время начала** рабочего дня (ЧЧ:ММ):\n"
            "Например: 10:00",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(GenerateScheduleStates.waiting_for_start_time)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ", reply_markup=get_cancel_keyboard())

@router.message(GenerateScheduleStates.waiting_for_start_time)
async def generate_schedule_start_time(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление расписания отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        datetime.strptime(message.text, "%H:%M")
        await state.update_data(start_time=message.text)
        await message.answer(
            "⏰ *Шаг 4 из 4 (продолжение)*\n\n"
            "Введите **время окончания** рабочего дня (ЧЧ:ММ):\n"
            "Например: 18:00\n\n"
            "✅ Слоты будут создаваться каждые 30 минут",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(GenerateScheduleStates.waiting_for_end_time)
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ", reply_markup=get_cancel_keyboard())

@router.message(GenerateScheduleStates.waiting_for_end_time)
async def generate_schedule_end_time(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление расписания отменено", reply_markup=get_admin_keyboard())
        return
    
    try:
        end_time_obj = datetime.strptime(message.text, "%H:%M")
        data = await state.get_data()
        start_time_obj = datetime.strptime(data['start_time'], "%H:%M")
        
        if end_time_obj <= start_time_obj:
            await message.answer("❌ Время окончания должно быть позже времени начала", reply_markup=get_cancel_keyboard())
            return
        
        # Парсим даты
        start_date = datetime.strptime(data['start_date'], "%d.%m.%Y")
        end_date = datetime.strptime(data['end_date'], "%d.%m.%Y")
        
        total_slots = 0
        days_count = 0
        current_date = start_date
        
        # Создаём расписание на каждый день в диапазоне
        while current_date <= end_date:
            date_str = current_date.strftime("%d.%m.%Y")
            slots = add_work_slots(
                data['master_id'],
                date_str,
                data['start_time'],
                message.text
            )
            total_slots += slots
            days_count += 1
            current_date += timedelta(days=1)
        
        master = get_master(data['master_id'])
        master_name = master['name'] if master else f"ID {data['master_id']}"
        
        await message.answer(
            f"✅ *Расписание успешно добавлено!*\n\n"
            f"👨‍🎨 Мастер: {master_name}\n"
            f"📅 Период: {data['start_date']} — {data['end_date']}\n"
            f"📆 Всего дней: {days_count}\n"
            f"⏰ Время работы: {data['start_time']} - {message.text}\n"
            f"⏱ Интервал: 30 минут\n"
            f"📊 Всего создано слотов: {total_slots}",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ", reply_markup=get_cancel_keyboard())