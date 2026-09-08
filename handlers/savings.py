import re
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.engine import async_session
from db.repository import SavingsGoalRepository, UserRepository
from keyboards.inline import main_menu
from services.calculator import format_currency, progress_bar

router = Router()


class SavingsStates(StatesGroup):
    name = State()
    target_amount = State()
    deadline = State()
    topup_amount = State()


def _savings_menu(goals: list, total: dict) -> str:
    lines = [f"🎯 Цели накопления\n"]
    if not goals:
        lines.append("Пока нет целей.\nДобавь первую цель!")
    else:
        for g in goals:
            pct = (g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0
            bar = progress_bar(pct)
            lines.append(f"**{g.name}**")
            lines.append(f"  {bar} {pct:.0f}%")
            lines.append(f"  {format_currency(g.current_amount)} / {format_currency(g.target_amount)}")
            if g.deadline:
                lines.append(f"  📅 {g.deadline}")
            lines.append("")
        lines.append(f"📊 Итого: {format_currency(total['total_saved'])} / {format_currency(total['total_target'])} ({total['pct']:.0f}%)")
    return "\n".join(lines)


def _goals_keyboard(goals: list) -> InlineKeyboardMarkup:
    buttons = []
    for g in goals:
        buttons.append([
            InlineKeyboardButton(text=f"💰 {g.name}", callback_data=f"savings:topup:{g.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"savings:del:{g.id}"),
        ])
    buttons.append([InlineKeyboardButton(text="➕ Новая цель", callback_data="savings:add")])
    buttons.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("savings"))
@router.callback_query(F.data == "menu:savings")
async def cmd_savings(message: Message | CallbackQuery):
    user_id = message.from_user.id
    async with async_session() as session:
        repo = SavingsGoalRepository(session)
        goals = await repo.get_active(user_id)
        total = await repo.get_total_progress(user_id)
        user_repo = UserRepository(session)
        user = await user_repo.get(user_id)

    text = _savings_menu(goals, total)
    if user and user.assets is not None and user.debts is not None:
        balance = user.assets - user.debts
        text += f"\n\n💰 Баланс: {format_currency(balance)} (активы - долги)"

    kb = _goals_keyboard(goals)
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        await message.answer()
    else:
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "savings:add")
async def add_goal_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🎯 Название цели:")
    await state.set_state(SavingsStates.name)
    await callback.answer()


@router.message(SavingsStates.name)
async def add_goal_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("💰 Целевая сумма (₽):")
    await state.set_state(SavingsStates.target_amount)


@router.message(SavingsStates.target_amount)
async def add_goal_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", ".").replace(" ", "").replace("₽", ""))
    except ValueError:
        await message.answer("⚠️ Введи число (например: 100000)")
        return
    await state.update_data(target_amount=amount)
    await message.answer("📅 Дедлайн (ГГГГ-ММ-ДД) или /skip:")
    await state.set_state(SavingsStates.deadline)


@router.message(SavingsStates.deadline)
async def add_goal_deadline(message: Message, state: FSMContext):
    data = await state.get_data()
    deadline = None
    if message.text and message.text.strip() != "/skip":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", message.text.strip()):
            await message.answer("⚠️ Формат: ГГГГ-ММ-ДД или /skip")
            return
        deadline = message.text.strip()

    async with async_session() as session:
        repo = SavingsGoalRepository(session)
        await repo.add(message.from_user.id, data["name"], data["target_amount"], deadline)
        goals = await repo.get_active(message.from_user.id)
        total = await repo.get_total_progress(message.from_user.id)

    await state.clear()
    await message.answer(_savings_menu(goals, total), reply_markup=_goals_keyboard(goals), parse_mode="Markdown")


@router.callback_query(F.data.startswith("savings:topup:"))
async def topup_goal_start(callback: CallbackQuery, state: FSMContext):
    goal_id = int(callback.data.split(":")[2])
    await state.update_data(goal_id=goal_id)
    await callback.message.edit_text("💰 Сумма пополнения (₽):")
    await state.set_state(SavingsStates.topup_amount)
    await callback.answer()


@router.message(SavingsStates.topup_amount)
async def topup_goal_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", ".").replace(" ", "").replace("₽", ""))
    except ValueError:
        await message.answer("⚠️ Введи число")
        return

    data = await state.get_data()
    async with async_session() as session:
        repo = SavingsGoalRepository(session)
        await repo.update_amount(data["goal_id"], message.from_user.id, amount)
        goals = await repo.get_active(message.from_user.id)
        total = await repo.get_total_progress(message.from_user.id)

    await state.clear()
    await message.answer(f"✅ +{format_currency(amount)}!\n\n" + _savings_menu(goals, total),
                         reply_markup=_goals_keyboard(goals), parse_mode="Markdown")


@router.callback_query(F.data.startswith("savings:del:"))
async def delete_goal(callback: CallbackQuery):
    goal_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        repo = SavingsGoalRepository(session)
        await repo.delete(goal_id, callback.from_user.id)
        goals = await repo.get_active(callback.from_user.id)
        total = await repo.get_total_progress(callback.from_user.id)

    await callback.message.edit_text(_savings_menu(goals, total),
                                     reply_markup=_goals_keyboard(goals), parse_mode="Markdown")
    await callback.answer("🗑 Удалено")
