from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from db.engine import async_session
from db.repository import ReminderRepository
from keyboards.inline import reminders_keyboard

router = Router()

REMINDER_TEXTS = {
    "daily": "📋 Какой твой главный финансовый шаг сегодня?",
    "weekly": "📊 Сколько ты заработал/потратил на этой неделе? Введи: /stats_week",
    "wisdom": "🧠 Финансовая мудрость дня. Введи: /wisdom",
    "plan_step": "🎯 Проверь свой план: /plan",
}


@router.callback_query(F.data == "menu:reminders")
async def cb_reminders_menu(callback: CallbackQuery):
    async with async_session() as session:
        repo = ReminderRepository(session)
        active = await repo.get_active(callback.from_user.id)
    active_types = [r.reminder_type for r in active]
    await callback.message.answer(
        "⏰ Настройка напоминаний\n\nВыбери, что включить/выключить:",
        reply_markup=reminders_keyboard(active_types),
    )
    await callback.answer()


@router.message(Command("reminders"))
async def cmd_reminders(message: Message):
    async with async_session() as session:
        repo = ReminderRepository(session)
        active = await repo.get_active(message.from_user.id)
    active_types = [r.reminder_type for r in active]
    await message.answer(
        "⏰ Настройка напоминаний\n\nВыбери, что включить/выключить:",
        reply_markup=reminders_keyboard(active_types),
    )


@router.callback_query(F.data.startswith("remind:"))
async def cb_toggle_reminder(callback: CallbackQuery):
    rtype = callback.data.split(":")[1]
    async with async_session() as session:
        repo = ReminderRepository(session)
        active = await repo.get_active(callback.from_user.id)
        active_types = [r.reminder_type for r in active]
        if rtype in active_types:
            await repo.remove(callback.from_user.id, rtype)
            status = "выключено"
        else:
            await repo.set(callback.from_user.id, rtype, "09:00")
            status = "включено"
        active = await repo.get_active(callback.from_user.id)
        active_types = [r.reminder_type for r in active]
    await callback.message.edit_reply_markup(reply_markup=reminders_keyboard(active_types))
    await callback.answer(f"{REMINDER_TEXTS.get(rtype, rtype)} — {status}")


@router.message(Command("send_reminders"))
async def cmd_send_reminders(message: Message):
    """Manual trigger for reminders (for testing)"""
    async with async_session() as session:
        repo = ReminderRepository(session)
        active = await repo.get_active(message.from_user.id)
    for rem in active:
        text = REMINDER_TEXTS.get(rem.reminder_type, "Напоминание")
        await message.answer(text)
