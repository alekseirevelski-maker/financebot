from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.engine import async_session
from db.repository import RecurringRepository, TransactionRepository
from keyboards.inline import main_menu
from templates.categories import CATEGORIES_RU as CATEGORY_RU

router = Router()


class SubStates(StatesGroup):
    name = State()
    amount = State()
    category = State()
    day = State()


@router.message(Command("sub"))
async def cmd_sub(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить платёж", callback_data="sub:add")],
        [InlineKeyboardButton(text="📋 Мои платежи", callback_data="sub:list")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")],
    ])
    await message.answer("💳 Регулярные платежи\n\nПодписки, кредиты, коммуналка, рассрочки — всё, что списывается каждый месяц.", reply_markup=keyboard)


@router.callback_query(F.data == "sub:add")
async def sub_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubStates.name)
    await callback.message.answer("📝 Название платежа:\n(например: Квартплата, Кредит, Netflix)")
    await callback.answer()


@router.message(SubStates.name)
async def sub_name(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено", reply_markup=main_menu())
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(SubStates.amount)
    await message.answer("💰 Сумма в ₽:")


@router.message(SubStates.amount)
async def sub_amount(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено", reply_markup=main_menu())
        return
    try:
        amount = float(message.text.strip().replace(",", ".").replace(" ", ""))
    except ValueError:
        await message.answer("⚠️ Введи число (например: 5000)")
        return
    await state.update_data(amount=amount)
    await state.set_state(SubStates.day)
    await message.answer("📅 День списания (1-31):")


@router.message(SubStates.day)
async def sub_day(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено", reply_markup=main_menu())
        return
    try:
        day = int(message.text.strip())
        if not (1 <= day <= 31):
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введи число от 1 до 31")
        return
    await state.update_data(day=day)

    buttons = []
    row = []
    for key, label in CATEGORY_RU.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"sub:cat:{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="sub:cancel")])

    await state.set_state(SubStates.category)
    await message.answer("🏷 Категория:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("sub:cat:"), SubStates.category)
async def sub_category(callback: CallbackQuery, state: FSMContext):
    cat = callback.data.split(":")[2]
    data = await state.get_data()
    await state.clear()

    async with async_session() as session:
        repo = RecurringRepository(session)
        await repo.add(
            user_id=callback.from_user.id,
            name=data["name"],
            amount=data["amount"],
            category=cat,
            day_of_month=data["day"],
        )

    cat_label = CATEGORY_RU.get(cat, cat)
    await callback.message.edit_text(
        f"✅ Платёж добавлен:\n\n"
        f"📝 {data['name']}\n"
        f"💰 {data['amount']:,.0f}₽\n"
        f"📅 День: {data['day']}\n"
        f"🏷 {cat_label}"
    )
    await callback.answer()


@router.callback_query(F.data == "sub:cancel")
async def sub_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено")
    await callback.answer()


@router.callback_query(F.data == "sub:list")
async def sub_list(callback: CallbackQuery):
    async with async_session() as session:
        repo = RecurringRepository(session)
        payments = await repo.get_active(callback.from_user.id)
        total = await repo.get_monthly_total(callback.from_user.id)

    if not payments:
        await callback.message.edit_text("📋 Нет активных платежей.\n\nДобавь первый: /sub")
        await callback.answer()
        return

    lines = [f"💳 Регулярные платежи ({len(payments)} шт.)\n"]
    for rp in payments:
        cat_label = CATEGORY_RU.get(rp.category, rp.category)
        lines.append(f"  • {rp.name} — {rp.amount:,.0f}₽ (день {rp.day_of_month}) {cat_label}")
    lines.append(f"\n{'─' * 30}")
    lines.append(f"💰 Итого в месяц: {total:,.0f}₽")

    buttons = [[InlineKeyboardButton(text=f"🗑 {rp.name} ({rp.amount:,.0f}₽)", callback_data=f"sub:del:{rp.id}")] for rp in payments]
    buttons.append([InlineKeyboardButton(text="➕ Добавить", callback_data="sub:add")])
    buttons.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")])

    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("sub:del:"))
async def sub_delete(callback: CallbackQuery):
    payment_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        repo = RecurringRepository(session)
        deleted = await repo.delete(callback.from_user.id, payment_id)

    if deleted:
        await callback.answer("✅ Удалено")
    else:
        await callback.answer("❌ Не найдено")

    # Обновляем список
    async with async_session() as session:
        repo = RecurringRepository(session)
        payments = await repo.get_active(callback.from_user.id)

    if payments:
        total = sum(rp.amount for rp in payments)
        lines = [f"💳 Регулярные платежи ({len(payments)} шт.)\n"]
        for rp in payments:
            cat_label = CATEGORY_RU.get(rp.category, rp.category)
            lines.append(f"  • {rp.name} — {rp.amount:,.0f}₽ (день {rp.day_of_month}) {cat_label}")
        lines.append(f"\n{'─' * 30}")
        lines.append(f"💰 Итого в месяц: {total:,.0f}₽")
        buttons = [[InlineKeyboardButton(text=f"🗑 {rp.name}", callback_data=f"sub:del:{rp.id}")] for rp in payments]
        buttons.append([InlineKeyboardButton(text="➕ Добавить", callback_data="sub:add")])
        buttons.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")])
        await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await callback.message.edit_text("📋 Нет активных платежей.\n\nДобавь: /sub")
