import asyncio
import logging
import sys
import pytz
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database import init_db
from handlers import router as client_router
from admin_handlers import router as admin_router
from utils import get_izhevsk_now

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def setup_commands():
    """Устанавливает команды бота в меню Telegram"""
    commands = [
        BotCommand(command="start", description="🚀 Начать работу"),
        BotCommand(command="services", description="💇‍♀️ Наши услуги"),
        BotCommand(command="masters", description="👨‍🎨 Наши мастера"),
        BotCommand(command="book", description="📅 Записаться на услугу"),
        BotCommand(command="mybookings", description="📋 Мои записи"),
        BotCommand(command="help", description="📖 Помощь"),
        BotCommand(command="admin", description="👑 Панель администратора"),
    ]
    await bot.set_my_commands(commands)

async def main():
    """Главная функция запуска бота"""
    logger.info("🟢 Запуск бота салона красоты...")
    
    # Инициализируем базу данных
    init_db()
    logger.info("🟢 База данных инициализирована")
    
    # Подключаем обработчики
    dp.include_router(client_router)
    dp.include_router(admin_router)
    logger.info("🟢 Обработчики подключены")
    
    # Устанавливаем команды
    await setup_commands()
    
    # Проверяем подключение к Telegram
    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот успешно запущен: @{me.username}")
        logger.info(f"✅ ID бота: {me.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения: {e}")
        logger.error("❌ Проверьте интернет и токен в файле .env")
        return
    
    # Запускаем поллинг
    logger.info("🟢 Запускаем поллинг...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        sys.exit(1)