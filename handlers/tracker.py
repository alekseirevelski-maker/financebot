import csv
import io
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from db.engine import async_session
from db.repository import TransactionRepository
from keyboards.inline import tracker_keyboard, main_menu
from templates.categories import CATEGORIES_RU

router = Router()

CATEGORIES = {
    "income": ["зарплата", "фриланс", "подработка", "инвестиции", "аренда", "подарок", "другое"],
    "expense": ["еда", "транспорт", "жильё", "коммуналка", "здоровье", "обучение", "развлечения", "одежда", "техника", "подписки", "другое"],
    "investment": ["акции", "облигации", "ETF", "крипто", "золото", "недвижимость", "другое"],
}


@router.callback_query(F.data == "menu:tracker")
async def cb_tracker(callback: CallbackQuery):
    await callback.message.answer(
        "💹 Трекер доходов/расходов\n\nВыбери действие:",
        reply_markup=tracker_keyboard(),
    )
    await callback.answer()


@router.message(Command("income"))
async def cmd_income(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Формат: /income 50000 зарплата")
        return
    try:
        amount = float(parts[1])
    except ValueError:
        await message.answer("Неверная сумма. Используй: /income 50000 зарплата")
        return
    category = parts[2] if len(parts) > 2 else "другое"
    async with async_session() as session:
        repo = TransactionRepository(session)
        await repo.add(message.from_user.id, "income", amount, category)
    await message.answer(f"💰 Записан доход: {amount:,.0f}₽ ({category})")


@router.message(Command("expense"))
async def cmd_expense(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Формат: /expense 3000 еда")
        return
    try:
        amount = float(parts[1])
    except ValueError:
        await message.answer("Неверная сумма. Используй: /expense 3000 еда")
        return
    category = parts[2] if len(parts) > 2 else "другое"
    async with async_session() as session:
        repo = TransactionRepository(session)
        await repo.add(message.from_user.id, "expense", amount, category)
    await message.answer(f"💸 Записан расход: {amount:,.0f}₽ ({category})")

    from handlers.budget import check_budget_alerts
    alert = await check_budget_alerts(message.from_user.id)
    if alert:
        await message.answer(alert)


@router.message(Command("invest"))
async def cmd_invest(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Формат: /invest 10000 облигации")
        return
    try:
        amount = float(parts[1])
    except ValueError:
        await message.answer("Неверная сумма. Используй: /invest 10000 облигации")
        return
    category = parts[2] if len(parts) > 2 else "другое"
    async with async_session() as session:
        repo = TransactionRepository(session)
        await repo.add(message.from_user.id, "investment", amount, category)
    await message.answer(f"📈 Записана инвестиция: {amount:,.0f}₽ ({category})")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    async with async_session() as session:
        repo = TransactionRepository(session)
        stats = await repo.get_month_stats(message.from_user.id)
    now = datetime.utcnow()
    sr = ((stats["income"] - stats["expense"]) / stats["income"] * 100) if stats["income"] > 0 else 0
    sr_emoji = "✅" if sr >= 30 else "⚠️" if sr >= 15 else "🚨"
    await message.answer(
        f"📊 Статистика за {now.strftime('%B %Y')}\n\n"
        f"Доходы:    {stats['income']:>12,.0f}₽\n"
        f"Расходы:   {stats['expense']:>12,.0f}₽\n"
        f"Инвестиции:{stats['investment']:>12,.0f}₽\n"
        f"{'─' * 30}\n"
        f"Чистый:    {stats['income'] - stats['expense']:>12,.0f}₽\n"
        f"Savings Rate: {sr:.1f}% {sr_emoji}\n"
        f"Операций: {stats['count']}"
    )


@router.message(Command("today"))
async def cmd_today(message: Message):
    from db.repository import RecurringRepository
    async with async_session() as session:
        repo = TransactionRepository(session)
        today = await repo.get_today_stats(message.from_user.id)
        sub_repo = RecurringRepository(session)
        sub_total = await sub_repo.get_monthly_total(message.from_user.id)

    lines = [f"📊 Сегодня — {datetime.utcnow().strftime('%d.%m.%Y')}\n"]

    if today["txs"]:
        for tx in today["txs"]:
            if tx.type == "income":
                lines.append(f"  💰 +{tx.amount:,.0f}₽ {tx.description or tx.category}")
            else:
                cat_label = CATEGORY_RU.get(tx.category, tx.category)
                lines.append(f"  💸 -{tx.amount:,.0f}₽ {cat_label} ({tx.description or '—'})")
        lines.append(f"\n{'─' * 30}")
        lines.append(f"Доходы:  {today['income']:>10,.0f}₽")
        lines.append(f"Расходы: {today['expense']:>10,.0f}₽")
        lines.append(f"Чистый:  {today['income'] - today['expense']:>10,.0f}₽")
    else:
        lines.append("  Пока нет операций.\n  Отправь фото чека или /expense")

    if sub_total > 0:
        lines.append(f"\n💳 Регулярные: {sub_total:,.0f}₽/мес")

    await message.answer("\n".join(lines), reply_markup=main_menu())


@router.message(Command("stats_week"))
async def cmd_stats_week(message: Message):
    async with async_session() as session:
        repo = TransactionRepository(session)
        stats = await repo.get_week_stats(message.from_user.id)
    sr = ((stats["income"] - stats["expense"]) / stats["income"] * 100) if stats["income"] > 0 else 0
    sr_emoji = "✅" if sr >= 30 else "⚠️" if sr >= 15 else "🚨"
    await message.answer(
        f"📊 Статистика за неделю\n\n"
        f"Доходы:    {stats['income']:>12,.0f}₽\n"
        f"Расходы:   {stats['expense']:>12,.0f}₽\n"
        f"Инвестиции:{stats['investment']:>12,.0f}₽\n"
        f"{'─' * 30}\n"
        f"Чистый:    {stats['income'] - stats['expense']:>12,.0f}₽\n"
        f"Savings Rate: {sr:.1f}% {sr_emoji}"
    )


@router.message(Command("export"))
async def cmd_export(message: Message):
    async with async_session() as session:
        repo = TransactionRepository(session)
        txs = await repo.get_all_csv(message.from_user.id)
    if not txs:
        await message.answer("Нет данных для экспорта.")
        return
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Дата", "Тип", "Сумма", "Категория", "Описание"])
    for tx in txs:
        writer.writerow([
            tx.date.strftime("%Y-%m-%d %H:%M"),
            tx.type,
            f"{tx.amount:.2f}",
            tx.category,
            tx.description or "",
        ])
    buf.seek(0)
    file = BufferedInputFile(buf.getvalue().encode(), filename="finance_export.csv")
    await message.answer_document(file, caption=f"📊 Экспорт: {len(txs)} операций")


@router.callback_query(F.data == "tracker:income")
async def cb_tracker_income(callback: CallbackQuery):
    await callback.message.answer("💰 Введи доход: /income 50000 зарплата")
    await callback.answer()


@router.callback_query(F.data == "tracker:expense")
async def cb_tracker_expense(callback: CallbackQuery):
    await callback.message.answer("💸 Введи расход: /expense 3000 еда")
    await callback.answer()


@router.callback_query(F.data == "tracker:invest")
async def cb_tracker_invest(callback: CallbackQuery):
    await callback.message.answer("📈 Введи инвестицию: /invest 10000 облигации")
    await callback.answer()


@router.callback_query(F.data == "tracker:stats")
async def cb_tracker_stats(callback: CallbackQuery):
    async with async_session() as session:
        repo = TransactionRepository(session)
        stats = await repo.get_month_stats(callback.from_user.id)
    now = datetime.utcnow()
    sr = ((stats["income"] - stats["expense"]) / stats["income"] * 100) if stats["income"] > 0 else 0
    sr_emoji = "✅" if sr >= 30 else "⚠️" if sr >= 15 else "🚨"
    await callback.message.answer(
        f"📊 {now.strftime('%B %Y')}\n"
        f"Доходы: {stats['income']:,.0f}₽ | Расходы: {stats['expense']:,.0f}₽\n"
        f"Чистый: {stats['income'] - stats['expense']:,.0f}₽ | SR: {sr:.1f}% {sr_emoji}"
    )
    await callback.answer()


@router.callback_query(F.data == "tracker:export")
async def cb_tracker_export(callback: CallbackQuery):
    async with async_session() as session:
        repo = TransactionRepository(session)
        txs = await repo.get_all_csv(callback.from_user.id)
    if not txs:
        await callback.message.answer("Нет данных для экспорта.")
        await callback.answer()
        return
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Дата", "Тип", "Сумма", "Категория", "Описание"])
    for tx in txs:
        writer.writerow([
            tx.date.strftime("%Y-%m-%d %H:%M"),
            tx.type,
            f"{tx.amount:.2f}",
            tx.category,
            tx.description or "",
        ])
    buf.seek(0)
    file = BufferedInputFile(buf.getvalue().encode(), filename="finance_export.csv")
    await callback.message.answer_document(file, caption=f"📊 Экспорт: {len(txs)} операций")
    await callback.answer()
