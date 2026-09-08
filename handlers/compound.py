from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from services.calculator import compound_future_value
from keyboards.inline import compound_keyboard

router = Router()


def _format_result(pmt: float, rate: float, months: int) -> str:
    result = compound_future_value(pmt, rate, months)
    years = months // 12
    rem_months = months % 12
    time_str = f"{years} лет {rem_months} мес" if years > 0 else f"{months} мес"
    mult = result['future_value'] / result['invested'] if result['invested'] > 0 else 0

    return (
        f"╔══════════════════════════╗\n"
        f"║  🧮 СЛОЖНЫЙ ПРОЦЕНТ      ║\n"
        f"╚══════════════════════════╝\n\n"
        f"💰 Взнос:    {pmt:>10,.0f}₽/мес\n"
        f"📈 Ставка:   {rate:>10}% годовых\n"
        f"⏱ Срок:     {time_str}\n\n"
        f"{'─' * 32}\n"
        f"📦 Вложено:  {result['invested']:>10,.0f}₽\n"
        f"💎 Прибыль:  {result['profit']:>10,.0f}₽\n"
        f"{'─' * 32}\n"
        f"🏆 Итого:    {result['future_value']:>10,.0f}₽\n"
        f"✨ Множитель: x{mult:.2f}"
    )


@router.callback_query(F.data == "menu:compound")
async def cb_compound_menu(callback: CallbackQuery):
    await callback.message.answer(
        "╔══════════════════════════╗\n"
        "║  🧮 КАЛЬКУЛЯТОР          ║\n"
        "╚══════════════════════════╝\n\n"
        "Выбери готовый расчёт\n"
        "или введи свой:\n"
        "/compound 10000 12 60",
        reply_markup=compound_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("compound:"))
async def cb_compound_quick(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    try:
        pmt = float(parts[1])
        rate = float(parts[2])
        months = int(parts[3])
    except ValueError:
        await callback.answer("Ошибка данных")
        return
    await callback.message.answer(_format_result(pmt, rate, months))
    await callback.answer()


@router.message(Command("compound"))
async def cmd_compound(message: Message):
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer(
            "Формат: /compound <сумма> <процент> <мес>\n\n"
            "Пример: /compound 10000 12 60\n"
            "→ 10000₽/мес, 12% годовых, 60 месяцев",
            reply_markup=compound_keyboard(),
        )
        return
    try:
        pmt = float(parts[1])
        rate = float(parts[2])
        months = int(parts[3])
    except (ValueError, IndexError):
        await message.answer("⚠️ Неверные данные. Формат: /compound 10000 12 60")
        return

    await message.answer(_format_result(pmt, rate, months))
