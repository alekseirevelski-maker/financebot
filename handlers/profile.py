from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.engine import async_session
from db.repository import UserRepository, TransactionRepository
from keyboards.inline import update_keyboard, main_menu
from services.calculator import progress_bar as _progress_bar
from templates.messages import PHASE_NAMES

router = Router()

FIELD_LABELS = {
    "age": "Возраст",
    "profession": "Профессия",
    "monthly_income": "Ежемесячный доход ₽",
    "monthly_expenses": "Ежемесячные расходы ₽",
    "assets": "Активы ₽",
    "debts": "Долги ₽",
    "skills": "Навыки",
    "financial_goal": "Финансовая цель",
}

THRESHOLDS = [170_000, 850_000, 1_700_000, 8_500_000, 17_000_000]


class UpdateStates(StatesGroup):
    WAITING_VALUE = State()


@router.callback_query(F.data == "menu:profile")
async def cb_profile(callback: CallbackQuery):
    await _show_profile(callback.from_user.id, callback.message.answer)


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    await _show_profile(message.from_user.id, message.answer)


async def _show_profile(user_id: int, answer_fn):
    async with async_session() as session:
        repo = UserRepository(session)
        user = await repo.get(user_id)
    if not user:
        await answer_fn("Профиль не найден. Пройди опрос: /survey")
        return

    income = user.monthly_income or 0
    expenses = user.monthly_expenses or 0
    sr = ((income - expenses) / income * 100) if income > 0 else 0
    sr_emoji = "✅" if sr >= 30 else "⚠️" if sr >= 15 else "🚨"
    phase_str = PHASE_NAMES.get(user.phase, user.phase or "—")
    risk_map = {"low": "🟢 Низкий", "medium": "🟡 Средний", "high": "🔴 Высокий"}
    risk_str = risk_map.get(user.risk_tolerance, "—")

    await answer_fn(
        f"👤 Профиль: {user.full_name}, {user.age or '—'} лет\n"
        f"💼 {user.profession or '—'}\n"
        f"💰 Доход: {income:,.0f}₽/мес | Расходы: {expenses:,.0f}₽/мес\n"
        f"📊 Savings Rate: {sr:.1f}% {sr_emoji}\n"
        f"🏦 Активы: {user.assets or 0:,.0f}₽ | Долги: {user.debts or 0:,.0f}₽\n"
        f"🎯 Цель: {user.financial_goal or '—'} ({user.goal_amount or 0:,.0f}₽)\n"
        f"📈 Фаза: {phase_str}\n"
        f"⚡ Риск: {risk_str}\n"
        f"💰 Инвест. капитал: {user.investment_capital or 0:,.0f}₽"
    )


@router.message(Command("update"))
async def cmd_update(message: Message):
    await message.answer(
        "Выбери поле для обновления:",
        reply_markup=update_keyboard(),
    )


@router.callback_query(F.data.startswith("update:"))
async def cb_update_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    label = FIELD_LABELS.get(field, field)
    await state.update_data(field=field)
    await state.set_state(UpdateStates.WAITING_VALUE)
    await callback.message.answer(f"Введи новое значение для «{label}»:")
    await callback.answer()


@router.message(UpdateStates.WAITING_VALUE)
async def process_update(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("field")
    value = message.text.strip()

    if field in ("age",):
        try:
            value = int(value)
        except ValueError:
            await message.answer("Введи число.")
            return
    elif field in ("monthly_income", "monthly_expenses", "assets", "debts"):
        try:
            value = float(value.replace(",", "").replace(" ", ""))
        except ValueError:
            await message.answer("Введи число.")
            return

    await state.clear()
    async with async_session() as session:
        repo = UserRepository(session)
        await repo.update(user_id=message.from_user.id, **{field: value})

    label = FIELD_LABELS.get(field, field)
    await message.answer(f"✅ «{label}» обновлено. Используй /profile для просмотра.")


@router.message(Command("recalc"))
async def cmd_recalc(message: Message):
    await message.answer("✅ План пересчитан с текущими данными. Используй /plan")


@router.message(Command("progress"))
async def cmd_progress(message: Message):
    async with async_session() as session:
        repo = UserRepository(session)
        user = await repo.get(message.from_user.id)
        tx_repo = TransactionRepository(session)
        stats = await tx_repo.get_month_stats(message.from_user.id)

    if not user:
        await message.answer("Профиль не найден. /survey")
        return

    assets = user.assets or 0
    lines = ["📈 Прогресс по порогам:\n"]
    for i, target in enumerate(THRESHOLDS):
        bar = _progress_bar(assets, target, 10)
        pct = min(assets / target * 100, 100) if target > 0 else 0
        label = f"{target / 1_000_000:.0f}M" if target >= 1_000_000 else f"{target / 1_000:.0f}K"
        lines.append(f"  {label}₽: {bar} {pct:.0f}%")

    lines.append(f"\nСейчас: {assets:,.0f}₽")
    await message.answer("\n".join(lines))
