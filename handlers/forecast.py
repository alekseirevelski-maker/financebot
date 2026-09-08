import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from db.engine import async_session
from db.repository import TransactionRepository, RecurringRepository, UserRepository
from keyboards.inline import main_menu
from services.forecasting import project_end_of_month, calculate_runway, savings_trajectory, format_runway, format_trajectory
from services.calculator import format_currency
from services.charts import forecast_trajectory
from utils.timezone import now as tz_now

router = Router()


def _forecast_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Конец месяца", callback_data="forecast:eom"),
            InlineKeyboardButton(text="⏰ Запас", callback_data="forecast:runway"),
        ],
        [
            InlineKeyboardButton(text="📈 Траектория", callback_data="forecast:trajectory"),
            InlineKeyboardButton(text="📊 График", callback_data="forecast:chart"),
        ],
        [
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
        ],
    ])


@router.message(Command("forecast"))
@router.callback_query(F.data == "menu:forecast")
async def cmd_forecast(message: Message | CallbackQuery):
    text = "🔮 Прогнозирование\n\nВыбери тип прогноза:"
    kb = _forecast_keyboard()
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=kb)
        await message.answer()
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "forecast:eom")
async def forecast_end_of_month(callback: CallbackQuery):
    await callback.answer("Расчитываю...")
    user_id = callback.from_user.id
    async with async_session() as session:
        tx_repo = TransactionRepository(session)
        month_stats = await tx_repo.get_month_stats(user_id)
        today_stats = await tx_repo.get_today_stats(user_id)

        sub_repo = RecurringRepository(session)
        recurring_total = await sub_repo.get_monthly_total(user_id)

    now = tz_now()
    days_in_month = 30
    days_remaining = days_in_month - now.day
    day_of_month = now.day

    daily_income = month_stats["income"] / day_of_month if day_of_month > 0 else 0
    daily_expense = month_stats["expense"] / day_of_month if day_of_month > 0 else 0

    # Get real balance from user profile
    async with async_session() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get(user_id)
    balance = (user.assets or 0) - (user.debts or 0) if user else 0

    result = project_end_of_month(
        current_balance=balance,
        daily_income=daily_income,
        daily_expenses=daily_expense,
        days_remaining=days_remaining,
        recurring_monthly=recurring_total,
    )

    text = (
        f"📅 Прогноз на конец месяца\n\n"
        f"Осталось дней: {result['days_remaining']}\n"
        f"Доход/день: {result['net_daily']:,.0f}₽\n"
        f"Регулярные: {recurring_total:,.0f}₽/мес\n\n"
        f"💰 Прогноз: **{format_currency(result['projected_balance'])}**\n\n"
        f"Текущий итого:\n"
        f"  Доход: {month_stats['income']:,.0f}₽\n"
        f"  Расход: {month_stats['expense']:,.0f}₽"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=_forecast_keyboard())


@router.callback_query(F.data == "forecast:runway")
async def forecast_runway(callback: CallbackQuery):
    await callback.answer("Расчитываю...")
    user_id = callback.from_user.id
    async with async_session() as session:
        tx_repo = TransactionRepository(session)
        month_stats = await tx_repo.get_month_stats(user_id)

        user_repo = UserRepository(session)
        user = await user_repo.get(user_id)

    balance = (user.assets or 0) - (user.debts or 0) if user else 0
    runway = calculate_runway(balance, month_stats["expense"], month_stats["income"])

    text = (
        f"⏰ Финансовый запас\n\n"
        f"Баланс: {format_currency(balance)}\n"
        f"Доход/мес: {month_stats['income']:,.0f}₽\n"
        f"Расход/мес: {month_stats['expense']:,.0f}₽\n\n"
        f"{format_runway(runway)}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=_forecast_keyboard())


@router.callback_query(F.data == "forecast:trajectory")
async def forecast_trajectory_cmd(callback: CallbackQuery):
    await callback.answer("Расчитываю...")
    user_id = callback.from_user.id
    async with async_session() as session:
        tx_repo = TransactionRepository(session)
        month_stats = await tx_repo.get_month_stats(user_id)

        user_repo = UserRepository(session)
        user = await user_repo.get(user_id)

    balance = (user.assets or 0) - (user.debts or 0) if user else 0
    monthly_savings = month_stats["income"] - month_stats["expense"]

    traj = savings_trajectory(balance, max(monthly_savings, 0), 12, 12.0)

    text = format_trajectory(traj)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=_forecast_keyboard())


@router.callback_query(F.data == "forecast:chart")
async def forecast_chart(callback: CallbackQuery):
    await callback.answer("Генерирую график...")
    user_id = callback.from_user.id
    async with async_session() as session:
        tx_repo = TransactionRepository(session)
        month_stats = await tx_repo.get_month_stats(user_id)

        user_repo = UserRepository(session)
        user = await user_repo.get(user_id)

    balance = (user.assets or 0) - (user.debts or 0) if user else 0
    monthly_savings = month_stats["income"] - month_stats["expense"]

    traj = savings_trajectory(balance, max(monthly_savings, 0), 12, 12.0)
    buf = await asyncio.to_thread(forecast_trajectory, traj)
    photo = BufferedInputFile(buf.read(), "forecast.png")
    await callback.message.answer_photo(photo, caption="📈 Прогноз накоплений на 12 мес.")
