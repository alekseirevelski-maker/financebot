import io
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.engine import async_session
from db.repository import TransactionRepository, RecurringRepository
from services.ocr import analyze_photo
from keyboards.inline import main_menu
from templates.categories import CATEGORIES_RU as CATEGORY_RU

router = Router()


class PhotoStates(StatesGroup):
    waiting_confirm = State()
    choosing_amount = State()
    choosing_date = State()
    choosing_merchant = State()
    choosing_category = State()


def _format_expense(data: dict) -> str:
    amount = data.get("amount", "—")
    merchant = data.get("merchant", "—") or "—"
    date = data.get("date", "—") or "—"
    cat_key = data.get("category", "other")
    cat_name = CATEGORY_RU.get(cat_key, cat_key)

    lines = [
        "📸 Распознано:\n",
        f"💰 Сумма: {amount}₽",
        f"🏪 Магазин: {merchant}",
        f"📅 Дата: {date}",
        f"🏷 Категория: {cat_name}",
    ]

    items = data.get("items", [])
    if items:
        lines.append("\n📝 Позиции:")
        for item in items[:10]:
            lines.append(f"  • {item.get('name', '?')} — {item.get('price', '?')}₽")
        if len(items) > 10:
            lines.append(f"  ... и ещё {len(items) - 10}")

    all_amounts = data.get("all_amounts", [])
    if len(all_amounts) > 1:
        lines.append("\n🔢 Все суммы на фото:")
        for i, amt in enumerate(all_amounts[:8]):
            marker = " ← итого" if amt == amount else ""
            lines.append(f"  {i+1}. {amt}₽{marker}")

    return "\n".join(lines)


def _confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="pc:save")],
        [
            InlineKeyboardButton(text="💰 Сумма", callback_data="pc:amount"),
            InlineKeyboardButton(text="🏷 Категория", callback_data="pc:category"),
        ],
        [
            InlineKeyboardButton(text="📅 Дата", callback_data="pc:date"),
            InlineKeyboardButton(text="🏪 Магазин", callback_data="pc:merchant"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="pc:cancel")],
    ])


def _category_kb():
    buttons = []
    row = []
    for key, label in CATEGORY_RU.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"pc:cat:{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="pc:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _amount_kb(amounts: list[float], current: float):
    buttons = []
    for amt in amounts[:6]:
        marker = " ✓" if amt == current else ""
        buttons.append([InlineKeyboardButton(text=f"{amt:,.0f}₽{marker}", callback_data=f"pc:setamt:{amt}")])
    buttons.append([InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="pc:manualamt")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="pc:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    await message.answer("🔍 Анализирую скриншот...")
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    image_bytes_io = io.BytesIO()
    await message.bot.download_file(file.file_path, image_bytes_io)
    result = await analyze_photo(image_bytes_io.getvalue())

    if result.get("amount") is None:
        await message.answer(
            "❌ Не удалось распознать сумму.\nПопробуй более чёткое фото или введи: /expense 1234 еда",
            reply_markup=main_menu(),
        )
        return

    await state.update_data(ocr_result=result)
    await state.set_state(PhotoStates.waiting_confirm)
    await message.answer(_format_expense(result), reply_markup=_confirm_kb())


@router.message(F.document)
async def handle_document(message: Message, state: FSMContext):
    doc = message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".pdf"):
        await message.answer("❌ Принимаю только PDF-файлы.\nИли отправь скриншот как фото.")
        return

    await message.answer("🔍 Анализирую PDF-выписку...")
    file = await message.bot.get_file(doc.file_id)
    pdf_bytes_io = io.BytesIO()
    await message.bot.download_file(file.file_path, pdf_bytes_io)

    from services.ocr import analyze_pdf
    result = analyze_pdf(pdf_bytes_io.getvalue())

    if result.get("amount") is None:
        await message.answer(
            "❌ Не удалось распознать сумму в PDF.\nПопробуй отправить скриншот или введи: /expense 1234 еда",
            reply_markup=main_menu(),
        )
        return

    await state.update_data(ocr_result=result)
    await state.set_state(PhotoStates.waiting_confirm)
    await message.answer(_format_expense(result), reply_markup=_confirm_kb())


@router.callback_query(F.data == "pc:save", PhotoStates.waiting_confirm)
async def save_expense(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ocr = data.get("ocr_result", {})
    await state.clear()

    async with async_session() as session:
        repo = TransactionRepository(session)
        await repo.add(
            user_id=callback.from_user.id, type_="expense",
            amount=ocr.get("amount", 0), category=ocr.get("category", "other"),
            description=ocr.get("merchant"), source="photo",
        )
        today = await repo.get_today_stats(callback.from_user.id)

    sub_total = 0
    async with async_session() as session:
        sub_total = await RecurringRepository(session).get_monthly_total(callback.from_user.id)

    cat_name = CATEGORY_RU.get(ocr.get("category", "other"), "")
    total_today = today["expense"]

    lines = [f"✅ Сохранено: {ocr.get('amount', 0):,.0f}₽ — {cat_name}\n"]
    lines.append(f"📊 Итого сегодня: {total_today:,.0f}₽ ({today['count']} операций)")
    if sub_total > 0:
        lines.append(f"💳 Регулярные: {sub_total:,.0f}₽/мес")

    await callback.message.edit_text("\n".join(lines))
    await callback.message.answer("Отправляй ещё фото или /today", reply_markup=main_menu())
    await callback.answer()

    from handlers.budget import check_budget_alerts
    alert = await check_budget_alerts(callback.from_user.id)
    if alert:
        await callback.message.answer(alert)


@router.callback_query(F.data == "pc:cancel", PhotoStates.waiting_confirm)
async def cancel_expense(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено")
    await callback.message.answer("Выбери действие:", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "pc:category", PhotoStates.waiting_confirm)
async def choose_category(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🏷 Выбери категорию:", reply_markup=_category_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("pc:cat:"), PhotoStates.waiting_confirm)
async def set_category(callback: CallbackQuery, state: FSMContext):
    cat_key = callback.data.split(":")[2]
    data = await state.get_data()
    ocr = data.get("ocr_result", {})
    ocr["category"] = cat_key
    await state.update_data(ocr_result=ocr)
    await state.set_state(PhotoStates.waiting_confirm)
    await callback.message.edit_text(_format_expense(ocr), reply_markup=_confirm_kb())
    await callback.answer()


@router.callback_query(F.data == "pc:back", PhotoStates.waiting_confirm)
async def back_to_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ocr = data.get("ocr_result", {})
    await callback.message.edit_text(_format_expense(ocr), reply_markup=_confirm_kb())
    await callback.answer()


@router.callback_query(F.data == "pc:amount", PhotoStates.waiting_confirm)
async def choose_amount(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ocr = data.get("ocr_result", {})
    all_amounts = ocr.get("all_amounts", [ocr.get("amount", 0)])
    current = ocr.get("amount", 0)
    await callback.message.edit_text(
        "💰 Выбери сумму:", reply_markup=_amount_kb(all_amounts, current)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pc:setamt:"), PhotoStates.waiting_confirm)
async def set_amount_from_kb(callback: CallbackQuery, state: FSMContext):
    amt = float(callback.data.split(":")[2])
    data = await state.get_data()
    ocr = data.get("ocr_result", {})
    ocr["amount"] = amt
    await state.update_data(ocr_result=ocr)
    await state.set_state(PhotoStates.waiting_confirm)
    await callback.message.edit_text(_format_expense(ocr), reply_markup=_confirm_kb())
    await callback.answer()


@router.callback_query(F.data == "pc:manualamt", PhotoStates.waiting_confirm)
async def ask_manual_amount(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("💰 Введи сумму (число):")
    await state.set_state(PhotoStates.choosing_amount)
    await callback.answer()


@router.message(PhotoStates.choosing_amount)
async def set_manual_amount(message: Message, state: FSMContext):
    try:
        value = float(message.text.strip().replace(",", ".").replace(" ", ""))
    except ValueError:
        await message.answer("⚠️ Введи число (например: 1234.50)")
        return
    data = await state.get_data()
    ocr = data.get("ocr_result", {})
    ocr["amount"] = value
    await state.update_data(ocr_result=ocr)
    await state.set_state(PhotoStates.waiting_confirm)
    await message.answer(_format_expense(ocr), reply_markup=_confirm_kb())


@router.callback_query(F.data == "pc:date", PhotoStates.waiting_confirm)
async def ask_date(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ocr = data.get("ocr_result", {})
    await callback.message.edit_text(f"📅 Текущая дата: {ocr.get('date', '—')}\n\nВведи новую (ГГГГ-ММ-ДД):")
    await state.set_state(PhotoStates.choosing_date)
    await callback.answer()


@router.message(PhotoStates.choosing_date)
async def set_manual_date(message: Message, state: FSMContext):
    import re
    date_text = message.text.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_text):
        await message.answer("⚠️ Формат: ГГГГ-ММ-ДД (например: 2025-01-15)")
        return
    data = await state.get_data()
    ocr = data.get("ocr_result", {})
    ocr["date"] = date_text
    await state.update_data(ocr_result=ocr)
    await state.set_state(PhotoStates.waiting_confirm)
    await message.answer(_format_expense(ocr), reply_markup=_confirm_kb())


@router.callback_query(F.data == "pc:merchant", PhotoStates.waiting_confirm)
async def ask_merchant(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ocr = data.get("ocr_result", {})
    await callback.message.edit_text(f"🏪 Текущий магазин: {ocr.get('merchant', '—')}\n\nВведи новое название:")
    await state.set_state(PhotoStates.choosing_merchant)
    await callback.answer()


@router.message(PhotoStates.choosing_merchant)
async def set_manual_merchant(message: Message, state: FSMContext):
    merchant = message.text.strip()
    if len(merchant) < 1 or len(merchant) > 100:
        await message.answer("⚠️ Название от 1 до 100 символов")
        return
    data = await state.get_data()
    ocr = data.get("ocr_result", {})
    ocr["merchant"] = merchant
    await state.update_data(ocr_result=ocr)
    await state.set_state(PhotoStates.waiting_confirm)
    await message.answer(_format_expense(ocr), reply_markup=_confirm_kb())
