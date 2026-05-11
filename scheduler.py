import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BOT_TOKEN
from database import get_tomorrow_bookings
from utils import get_tomorrow_str
from aiogram import Bot

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

async def send_daily_reminders():
    # Отправляет напоминания о записях на завтра
    logger.info("🕐 Проверяю записи на завтра...")
    
    bookings = get_tomorrow_bookings()
    tomorrow_str = get_tomorrow_str()
    
    if not bookings:
        logger.info("📭 Записей на завтра нет")
        return
    
    success_count = 0
    for booking in bookings:
        try:
            text = (
                f"📢 *Напоминание о записи в салон красоты!*\n\n"
                f"Здравствуйте, {booking['client_name']}! 👋\n\n"
                f"Напоминаем, что завтра, {tomorrow_str}, "
                f"в {booking['booking_time']} у вас запись:\n\n"
                f"💇‍♀️ *Услуга:* {booking['service_name']}\n"
                f"👨‍🎨 *Мастер:* {booking['master_name']}\n\n"
                f"✨ Ждём вас в салоне «Бабочка»!\n"
                f"📍 Адрес: г. Ижевск, ул. Пушкинская, 123\n\n"
                f"Если вы не можете прийти, отмените запись через /mybookings заранее. 💕"
            )
            await bot.send_message(
                chat_id=booking['telegram_id'],
                text=text,
                parse_mode="Markdown"
            )
            logger.info(f"✅ Напоминание отправлено клиенту {booking['client_name']}")
            success_count += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")
    
    logger.info(f"📨 Отправлено {success_count} из {len(bookings)} напоминаний")


def setup_scheduler():
    # Настраивает и запускает планировщик задач
    try:
        scheduler = AsyncIOScheduler(timezone="Europe/Samara")
        
        scheduler.add_job(
            send_daily_reminders,
            trigger=CronTrigger(hour=19, minute=00),
            id="daily_reminders",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("🕐 Планировщик запущен. Напоминания в 19:00")
        return scheduler
    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика: {e}")
        return None
