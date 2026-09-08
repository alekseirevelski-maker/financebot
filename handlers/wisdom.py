import random
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from services.strategies import STRATEGIES, THINKER_NAMES
from keyboards.inline import wisdom_keyboard

router = Router()


def get_wisdom_text(key: str | None = None) -> str:
    if key and key in STRATEGIES:
        s = STRATEGIES[key]
        principle = random.choice(s["principles"])
        quote = random.choice(s["quotes"])
        return (
            f"🧠 {s['name']}\n\n"
            f"Принцип: {principle}\n\n"
            f"Цитата: {quote}"
        )
    key = random.choice(list(STRATEGIES.keys()))
    s = STRATEGIES[key]
    principle = random.choice(s["principles"])
    quote = random.choice(s["quotes"])
    return (
        f"🧠 {s['name']}\n\n"
        f"Принцип: {principle}\n\n"
        f"Цитата: {quote}"
    )


@router.callback_query(F.data == "menu:wisdom")
async def cb_wisdom_menu(callback: CallbackQuery):
    await callback.message.answer(
        "🧠 Финансовая мудрость\n\nВыбери мыслителя или получи случайную цитату:",
        reply_markup=wisdom_keyboard(),
    )
    await callback.answer()


@router.message(Command("wisdom"))
async def cmd_wisdom(message: Message):
    parts = message.text.split()
    key = parts[1].lower() if len(parts) > 1 else None
    if key and key not in STRATEGIES:
        await message.answer(
            f"Доступные мыслители: {', '.join(THINKER_NAMES.values())}\nИли просто: /wisdom"
        )
        return
    await message.answer(get_wisdom_text(key))


@router.callback_query(F.data.startswith("wisdom:"))
async def cb_wisdom(callback: CallbackQuery):
    key = callback.data.split(":")[1]
    if key == "random":
        key = None
    await callback.message.answer(get_wisdom_text(key))
    await callback.answer()


@router.message(Command("principles"))
async def cmd_principles(message: Message):
    parts = message.text.split()
    page = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    keys = list(STRATEGIES.keys())
    if page >= len(keys):
        page = 0
    key = keys[page]
    s = STRATEGIES[key]
    text = (
        f"📖 Принципы ({page + 1}/{len(keys)})\n\n"
        f"🧠 {s['name']}:\n\n"
    )
    for p in s["principles"]:
        text += f"  • {p}\n"
    text += f"\nЕщё: /principles {page + 1}"
    await message.answer(text)
