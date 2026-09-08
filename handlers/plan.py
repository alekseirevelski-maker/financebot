from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from db.engine import async_session
from db.repository import UserRepository
from services.plan_engine import generate_plan
from keyboards.inline import plan_nav, main_menu
from templates.messages import PLAN_HEADERS

router = Router()


@router.message(Command("plan"))
async def cmd_plan(message: Message):
    async with async_session() as session:
        repo = UserRepository(session)
        user = await repo.get(message.from_user.id)
    if not user or not user.survey_completed:
        await message.answer("Сначала пройди опрос: /survey")
        return
    plan = generate_plan(user)
    await message.answer(plan[0], reply_markup=plan_nav(0, len(plan)))


@router.message(Command("plan_step"))
async def cmd_plan_step(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /plan 3 (номер этапа 1-7)")
        return
    step = int(parts[1]) - 1
    async with async_session() as session:
        repo = UserRepository(session)
        user = await repo.get(message.from_user.id)
    if not user or not user.survey_completed:
        await message.answer("Сначала пройди опрос: /survey")
        return
    plan = generate_plan(user)
    if 0 <= step < len(plan):
        await message.answer(plan[step], reply_markup=plan_nav(step, len(plan)))
    else:
        await message.answer("Этап не найден (1-7).")


@router.callback_query(F.data.startswith("plan:"))
async def cb_plan(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    if action == "noop":
        await callback.answer()
        return
    step = int(action)
    async with async_session() as session:
        repo = UserRepository(session)
        user = await repo.get(callback.from_user.id)
    if not user or not user.survey_completed:
        await callback.message.answer("Сначала пройди опрос: /survey")
        await callback.answer()
        return
    plan = generate_plan(user)
    if 0 <= step < len(plan):
        await callback.message.edit_text(plan[step], reply_markup=plan_nav(step, len(plan)))
    await callback.answer()
