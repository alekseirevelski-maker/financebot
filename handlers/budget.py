from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.engine import async_session
from db.repository import BudgetRepository, TransactionRepository
from keyboards.inline import main_menu
from templates.categories import CATEGORIES_RU, EXPENSE_CATEGORIES
from services.calculator import format_currency, progress_bar

router = Router()


class BudgetStates(StatesGroup):
    choosing_category = State()
    setting_limit = State()


def _budget_menu(report: list) -> str:
    lines = [f"📋 Бюджет на месяц\n"]
    if not report:
        lines.append("Пока нет бюджетов.\nУстанови лимит по категориям!")
    else:
        for b in report:
            bar = progress_bar(b["pct"])
            emoji = "✅" if b["status"] == "ok" else "⚠️" if b["status"] == "warning" else "🚨"
            cat_label = CATEGORIES_RU.get(b["category"], b["category"])
            lines.append(f"{emoji} **{cat_label}**")
            lines.append(f"  {bar} {b['pct']:.0f}%")
            lines.append(f"  {format_currency(b['spent'])} / {format_currency(b['limit'])}")
            lines.append(f"  Остаток: {format_currency(b['remaining'])}")
            lines.append("")
    return "\n".join(lines)


def _budget_keyboard(report: list) -> InlineKeyboardMarkup:
    buttons = []
    for b in report:
        cat_label = CATEGORIES_RU.get(b["category"], b["category"])
        buttons.append([
            InlineKeyboardButton(text=f"📋 {cat_label}", callback_data=f"budget:set:{b['category']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"budget:del:{b['category']}"),
        ])
    buttons.append([InlineKeyboardButton(text="➕ Установить лимит", callback_data="budget:add")])
    buttons.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _category_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for cat in EXPENSE_CATEGORIES:
        label = CATEGORIES_RU.get(cat, cat)
        row.append(InlineKeyboardButton(text=label, callback_data=f"budget:cat:{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="menu:budget")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("budget"))
@router.callback_query(F.data == "menu:budget")
async def cmd_budget(message: Message | CallbackQuery):
    user_id = message.from_user.id
    async with async_session() as session:
        repo = BudgetRepository(session)
        report = await repo.get_spending_vs_budget(user_id)

    text = _budget_menu(report)
    kb = _budget_keyboard(report)
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        await message.answer()
    else:
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "budget:add")
async def add_budget_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📋 Выбери категорию:", reply_markup=_category_keyboard())
    await state.set_state(BudgetStates.choosing_category)
    await callback.answer()


@router.callback_query(F.data.startswith("budget:cat:"))
async def choose_budget_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[2]
    await state.update_data(category=category)
    cat_label = CATEGORIES_RU.get(category, category)
    await callback.message.edit_text(f"💰 Лимит для **{cat_label}** (₽/мес):", parse_mode="Markdown")
    await state.set_state(BudgetStates.setting_limit)
    await callback.answer()


@router.message(BudgetStates.setting_limit)
async def set_budget_limit(message: Message, state: FSMContext):
    try:
        limit = float(message.text.strip().replace(",", ".").replace(" ", "").replace("₽", ""))
    except ValueError:
        await message.answer("⚠️ Введи число (например: 5000)")
        return

    data = await state.get_data()
    async with async_session() as session:
        repo = BudgetRepository(session)
        await repo.set_budget(message.from_user.id, data["category"], limit)
        report = await repo.get_spending_vs_budget(message.from_user.id)

    await state.clear()
    await message.answer(_budget_menu(report), reply_markup=_budget_keyboard(report), parse_mode="Markdown")


@router.callback_query(F.data.startswith("budget:del:"))
async def delete_budget(callback: CallbackQuery):
    category = callback.data.split(":")[2]
    async with async_session() as session:
        repo = BudgetRepository(session)
        budgets = await repo.get_budgets(callback.from_user.id)
        for b in budgets:
            if b.category == category:
                await repo.delete_budget(b.id, callback.from_user.id)
                break
        report = await repo.get_spending_vs_budget(callback.from_user.id)

    await callback.message.edit_text(_budget_menu(report), reply_markup=_budget_keyboard(report), parse_mode="Markdown")
    await callback.answer("🗑 Удалено")


async def check_budget_alerts(user_id: int) -> str | None:
    """Check if any budget is at 80%+ and return warning message."""
    async with async_session() as session:
        repo = BudgetRepository(session)
        report = await repo.get_spending_vs_budget(user_id)

    warnings = []
    for b in report:
        if b["status"] == "warning":
            cat_label = CATEGORIES_RU.get(b["category"], b["category"])
            warnings.append(f"⚠️ {cat_label}: потрачено {b['pct']:.0f}% бюджета ({format_currency(b['spent'])}/{format_currency(b['limit'])})")
        elif b["status"] == "over":
            cat_label = CATEGORIES_RU.get(b["category"], b["category"])
            warnings.append(f"🚨 {cat_label}: ПРЕВЫШЕН лимит! ({format_currency(b['spent'])}/{format_currency(b['limit'])})")

    return "\n".join(warnings) if warnings else None
