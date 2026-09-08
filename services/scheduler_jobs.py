"""Background jobs for APScheduler — reminder delivery."""

from datetime import datetime
from aiogram import Bot
from loguru import logger
from db.engine import async_session
from db.repository import ReminderRepository

REMINDER_TEXTS = {
    "daily": "📋 Какой твой главный финансовый шаг сегодня?",
    "weekly": "📊 Сколько ты заработал/потратил на этой неделе? /stats_week",
    "wisdom": "🧠 Финансовая мудрость дня. /wisdom",
    "plan_step": "🎯 Проверь свой план: /plan",
}


async def check_reminders(bot: Bot):
    """Check all active reminders and send if their time matches."""
    now = datetime.utcnow()
    current_minute = now.hour * 60 + now.minute

    async with async_session() as session:
        repo = ReminderRepository(session)
        all_active = await repo.get_all_active_users()

    sent = 0
    for rem in all_active:
        try:
            parts = rem.time_of_day.split(":")
            rem_minute = int(parts[0]) * 60 + int(parts[1])
            if 0 <= (current_minute - rem_minute) < 5:
                text = REMINDER_TEXTS.get(rem.reminder_type, "Напоминание")
                await bot.send_message(chat_id=rem.user_id, text=text)
                sent += 1
        except Exception as e:
            logger.warning("Reminder send failed for user %s: %s", rem.user_id, e)

    if sent:
        logger.info("Отправлено %d напоминаний", sent)
