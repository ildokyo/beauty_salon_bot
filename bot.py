import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database import init_db
from handlers import router as client_router
from admin_handlers import router as admin_router
from scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def setup_commands():
    commands = [
        BotCommand(command="start", description="🚀 Начать работу"),
        BotCommand(command="services", description="💇‍♀️ Услуги"),
        BotCommand(command="masters", description="👨‍🎨 Мастера"),
        BotCommand(command="book", description="📅 Записаться"),
        BotCommand(command="mybookings", description="📋 Мои записи"),
        BotCommand(command="help", description="📖 Помощь"),
        BotCommand(command="admin", description="👑 Админ панель"),
    ]
    await bot.set_my_commands(commands)

async def main():
    logger.info("🟢 Запуск бота салона красоты...")
    
    init_db()
    logger.info("🟢 База данных инициализирована")
    
    scheduler = setup_scheduler()
    
    dp.include_router(client_router)
    dp.include_router(admin_router)
    logger.info("🟢 Обработчики подключены")
    
    await setup_commands()
    
    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот запущен: @{me.username}")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return
    
    logger.info("🟢 Запускаем поллинг...")
    
    try:
        await dp.start_polling(bot)
    finally:
        if scheduler:
            scheduler.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
        sys.exit(0)