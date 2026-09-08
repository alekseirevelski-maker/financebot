import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from db.engine import async_session
from db.repository import TransactionRepository
from keyboards.inline import main_menu
from templates.categories import CATEGORIES_RU
from services.charts import (
    expense_pie_chart, income_vs_expenses_bar, monthly_trend_line,
    top_categories_bar, savings_rate_timeline
)

router = Router()


def _analytics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🥧 Расходы", callback_data="analytics:pie"),
            InlineKeyboardButton(text="📊 Доход/Расход", callback_data="analytics:bar"),
        ],
        [
            InlineKeyboardButton(text="📈 Тренд", callback_data="analytics:trend"),
            InlineKeyboardButton(text="🔝 Топ категории", callback_data="analytics:top"),
        ],
        [
            InlineKeyboardButton(text="💰 Норма сбережений", callback_data="analytics:sr"),
        ],
        [
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
        ],
    ])


@router.message(Command("analytics"))
@router.callback_query(F.data == "menu:analytics")
async def cmd_analytics(message: Message | CallbackQuery):
    text = "📈 Аналитика\n\nВыбери тип графика:"
    kb = _analytics_keyboard()
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=kb)
        await message.answer()
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "analytics:pie")
async def chart_expense_pie(callback: CallbackQuery):
    await callback.answer("Генерирую график...")
    async with async_session() as session:
        repo = TransactionRepository(session)
        raw = await repo.get_expenses_by_category(callback.from_user.id)

    if not raw:
        await callback.message.answer("📊 Пока нет расходов для анализа")
        return

    labeled = {CATEGORIES_RU.get(k, k): v for k, v in raw.items()}
    buf = await asyncio.to_thread(expense_pie_chart, labeled)
    photo = BufferedInputFile(buf.read(), "expense_pie.png")
    await callback.message.answer_photo(photo, caption="📊 Расходы по категориям")


@router.callback_query(F.data == "analytics:bar")
async def chart_income_expenses(callback: CallbackQuery):
    await callback.answer("Генерирую график...")
    async with async_session() as session:
        repo = TransactionRepository(session)
        monthly = await repo.get_monthly_totals(callback.from_user.id, 6)

    if not any(m["income"] > 0 or m["expense"] > 0 for m in monthly):
        await callback.message.answer("📊 Пока нет данных для графика")
        return

    buf = await asyncio.to_thread(income_vs_expenses_bar, monthly)
    photo = BufferedInputFile(buf.read(), "income_expenses.png")
    await callback.message.answer_photo(photo, caption="📊 Доходы vs Расходы за 6 месяцев")


@router.callback_query(F.data == "analytics:trend")
async def chart_trend(callback: CallbackQuery):
    await callback.answer("Генерирую график...")
    async with async_session() as session:
        repo = TransactionRepository(session)
        monthly = await repo.get_monthly_totals(callback.from_user.id, 6)

    if not any(m["income"] > 0 or m["expense"] > 0 for m in monthly):
        await callback.message.answer("📊 Пока нет данных для графика")
        return

    buf = await asyncio.to_thread(monthly_trend_line, monthly)
    photo = BufferedInputFile(buf.read(), "trend.png")
    await callback.message.answer_photo(photo, caption="📈 Тренд по месяцам")


@router.callback_query(F.data == "analytics:top")
async def chart_top_categories(callback: CallbackQuery):
    await callback.answer("Генерирую график...")
    async with async_session() as session:
        repo = TransactionRepository(session)
        raw = await repo.get_expenses_by_category(callback.from_user.id)

    if not raw:
        await callback.message.answer("📊 Пока нет расходов для анализа")
        return

    labeled = {CATEGORIES_RU.get(k, k): v for k, v in raw.items()}
    buf = await asyncio.to_thread(top_categories_bar, labeled)
    photo = BufferedInputFile(buf.read(), "top_categories.png")
    await callback.message.answer_photo(photo, caption="🔝 Топ категорий расходов")


@router.callback_query(F.data == "analytics:sr")
async def chart_savings_rate(callback: CallbackQuery):
    await callback.answer("Генерирую график...")
    async with async_session() as session:
        repo = TransactionRepository(session)
        sr_data = await repo.get_savings_rate_history(callback.from_user.id, 6)

    if not sr_data or all(sr == 0 for _, sr in sr_data):
        await callback.message.answer("📊 Пока нет данных для расчёта нормы сбережений")
        return

    buf = await asyncio.to_thread(savings_rate_timeline, sr_data)
    photo = BufferedInputFile(buf.read(), "savings_rate.png")
    await callback.message.answer_photo(photo, caption="💰 Норма сбережений по месяцам")
