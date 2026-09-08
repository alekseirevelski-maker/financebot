import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from db.engine import async_session
from db.repository import TransactionRepository, BudgetRepository, SavingsGoalRepository, UserRepository
from keyboards.inline import main_menu
from services.reports import generate_monthly_report, generate_weekly_report

router = Router()


def _reports_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Месячный", callback_data="reports:monthly"),
            InlineKeyboardButton(text="📄 Недельный", callback_data="reports:weekly"),
        ],
        [
            InlineKeyboardButton(text="📊 Сравнение", callback_data="reports:compare"),
        ],
        [
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
        ],
    ])


@router.message(Command("report"))
@router.callback_query(F.data == "menu:reports")
async def cmd_report(message: Message | CallbackQuery):
    text = "📄 Отчёты\n\nВыбери тип отчёта:"
    kb = _reports_keyboard()
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=kb)
        await message.answer()
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "reports:monthly")
async def report_monthly(callback: CallbackQuery):
    await callback.answer("Генерирую отчёт...")
    user_id = callback.from_user.id
    async with async_session() as session:
        tx_repo = TransactionRepository(session)
        tx_stats = await tx_repo.get_month_stats(user_id)

        budget_repo = BudgetRepository(session)
        budget_data = await budget_repo.get_spending_vs_budget(user_id)

        savings_repo = SavingsGoalRepository(session)
        savings_data = await savings_repo.get_total_progress(user_id)

    buf = await asyncio.to_thread(
        generate_monthly_report,
        {"user_id": user_id},
        tx_stats,
        budget_data,
        savings_data,
    )
    doc = BufferedInputFile(buf.read(), f"report_{callback.from_user.id}.pdf")
    await callback.message.answer_document(doc, caption="📄 Месячный отчёт")


@router.callback_query(F.data == "reports:weekly")
async def report_weekly(callback: CallbackQuery):
    await callback.answer("Генерирую отчёт...")
    user_id = callback.from_user.id
    async with async_session() as session:
        tx_repo = TransactionRepository(session)
        tx_stats = await tx_repo.get_week_stats(user_id)

    buf = await asyncio.to_thread(
        generate_weekly_report,
        {"user_id": user_id},
        tx_stats,
    )
    doc = BufferedInputFile(buf.read(), f"weekly_{callback.from_user.id}.pdf")
    await callback.message.answer_document(doc, caption="📄 Недельный отчёт")


@router.callback_query(F.data == "reports:compare")
async def report_compare(callback: CallbackQuery):
    await callback.answer("Генерирую сравнение...")
    user_id = callback.from_user.id
    async with async_session() as session:
        tx_repo = TransactionRepository(session)
        data = await tx_repo.get_comparison_data(user_id)

    cur = data["current"]
    prev = data["previous"]

    def _diff(a, b):
        if b == 0:
            return "∞" if a > 0 else "0%"
        d = (a - b) / b * 100
        return f"+{d:.0f}%" if d > 0 else f"{d:.0f}%"

    text = (
        f"📊 Сравнение периодов\n\n"
        f"**Текущий месяц:**\n"
        f"  Доход: {cur['income']:,.0f}₽\n"
        f"  Расход: {cur['expense']:,.0f}₽\n"
        f"  Чистый: {cur['income'] - cur['expense']:,.0f}₽\n\n"
        f"**Прошлый месяц:**\n"
        f"  Доход: {prev['income']:,.0f}₽\n"
        f"  Расход: {prev['expense']:,.0f}₽\n"
        f"  Чистый: {prev['income'] - prev['expense']:,.0f}₽\n\n"
        f"**Изменения:**\n"
        f"  Доход: {_diff(cur['income'], prev['income'])}\n"
        f"  Расход: {_diff(cur['expense'], prev['expense'])}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=_reports_keyboard())
