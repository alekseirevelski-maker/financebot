from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.engine import async_session
from db.repository import UserRepository
from keyboards.inline import risk_keyboard, phase_keyboard, main_menu
from templates.messages import SURVEY_QUESTIONS, SURVEY_STEP_LABELS, SURVEY_START, SURVEY_DONE

router = Router()


class SurveyStates(StatesGroup):
    AGE = State()
    PROFESSION = State()
    MONTHLY_INCOME = State()
    MONTHLY_EXPENSES = State()
    ASSETS = State()
    DEBTS = State()
    FREE_HOURS = State()
    INVESTMENT_CAPITAL = State()
    SKILLS = State()
    FINANCIAL_GOAL = State()
    GOAL_AMOUNT = State()
    RISK_TOLERANCE = State()
    PHASE = State()


STEP_TO_STATE = [
    SurveyStates.AGE, SurveyStates.PROFESSION, SurveyStates.MONTHLY_INCOME,
    SurveyStates.MONTHLY_EXPENSES, SurveyStates.ASSETS, SurveyStates.DEBTS,
    SurveyStates.FREE_HOURS, SurveyStates.INVESTMENT_CAPITAL, SurveyStates.SKILLS,
    SurveyStates.FINANCIAL_GOAL, SurveyStates.GOAL_AMOUNT,
]


@router.message(Command("survey"))
async def cmd_survey(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SurveyStates.AGE)
    step_text = SURVEY_QUESTIONS[0][0]
    await message.answer(
        SURVEY_START.format(step=f"Шаг 1/13: {step_text}")
    )


@router.callback_query(F.data == "survey:start")
async def cb_survey_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(SurveyStates.AGE)
    step_text = SURVEY_QUESTIONS[0][0]
    await callback.message.answer(
        SURVEY_START.format(step=f"Шаг 1/13: {step_text}")
    )
    await callback.answer()


async def process_step(message: Message, state: FSMContext, step_index: int, field: str, expected_type: type):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Опрос отменён. /survey — начать заново")
        return False

    text = message.text.strip()
    try:
        value = expected_type(text)
        if expected_type in (int, float) and value < 0:
            raise ValueError
        if field == "age" and not (16 <= value <= 100):
            await message.answer("⚠️ Возраст должен быть от 16 до 100.")
            return False
    except (ValueError, TypeError):
        type_name = "число" if expected_type != str else "текст"
        await message.answer(f"⚠️ Введи {type_name}.")
        return False

    await state.update_data(**{field: value})

    next_index = step_index + 1
    if next_index < len(SURVEY_QUESTIONS):
        next_q = SURVEY_QUESTIONS[next_index]
        next_state = STEP_TO_STATE[next_index]
        await state.set_state(next_state)
        await message.answer(
            SURVEY_START.format(step=f"Шаг {next_index + 1}/13: {next_q[0]}")
        )
    else:
        await state.set_state(SurveyStates.RISK_TOLERANCE)
        await message.answer(
            SURVEY_START.format(step="Шаг 12/13: Какая толерантность к риску?")
        )
        await message.answer("Выбери вариант 👇", reply_markup=risk_keyboard())
    return True


@router.message(SurveyStates.AGE)
async def survey_age(message: Message, state: FSMContext):
    await process_step(message, state, 0, "age", int)


@router.message(SurveyStates.PROFESSION)
async def survey_profession(message: Message, state: FSMContext):
    await process_step(message, state, 1, "profession", str)


@router.message(SurveyStates.MONTHLY_INCOME)
async def survey_income(message: Message, state: FSMContext):
    await process_step(message, state, 2, "monthly_income", float)


@router.message(SurveyStates.MONTHLY_EXPENSES)
async def survey_expenses(message: Message, state: FSMContext):
    await process_step(message, state, 3, "monthly_expenses", float)


@router.message(SurveyStates.ASSETS)
async def survey_assets(message: Message, state: FSMContext):
    await process_step(message, state, 4, "assets", float)


@router.message(SurveyStates.DEBTS)
async def survey_debts(message: Message, state: FSMContext):
    await process_step(message, state, 5, "debts", float)


@router.message(SurveyStates.FREE_HOURS)
async def survey_hours(message: Message, state: FSMContext):
    await process_step(message, state, 6, "free_hours", float)


@router.message(SurveyStates.INVESTMENT_CAPITAL)
async def survey_invest(message: Message, state: FSMContext):
    await process_step(message, state, 7, "investment_capital", float)


@router.message(SurveyStates.SKILLS)
async def survey_skills(message: Message, state: FSMContext):
    await process_step(message, state, 8, "skills", str)


@router.message(SurveyStates.FINANCIAL_GOAL)
async def survey_goal(message: Message, state: FSMContext):
    await process_step(message, state, 9, "financial_goal", str)


@router.message(SurveyStates.GOAL_AMOUNT)
async def survey_goal_amount(message: Message, state: FSMContext):
    await process_step(message, state, 10, "goal_amount", float)


@router.callback_query(F.data.startswith("risk:"))
async def survey_risk(callback: CallbackQuery, state: FSMContext):
    risk = callback.data.split(":")[1]
    await state.update_data(risk_tolerance=risk)
    await state.set_state(SurveyStates.PHASE)
    await callback.message.answer(
        SURVEY_START.format(step="Шаг 13/13: Какая у тебя фаза?")
    )
    await callback.message.answer("Выбери 👇", reply_markup=phase_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("phase:"), SurveyStates.PHASE)
async def survey_phase(callback: CallbackQuery, state: FSMContext):
    phase = callback.data.split(":")[1]
    data = await state.get_data()
    await state.clear()

    async with async_session() as session:
        repo = UserRepository(session)
        await repo.update(
            user_id=callback.from_user.id,
            age=data.get("age"),
            profession=data.get("profession"),
            monthly_income=data.get("monthly_income"),
            monthly_expenses=data.get("monthly_expenses"),
            assets=data.get("assets"),
            debts=data.get("debts"),
            free_hours=data.get("free_hours"),
            investment_capital=data.get("investment_capital"),
            skills=data.get("skills"),
            financial_goal=data.get("financial_goal"),
            goal_amount=data.get("goal_amount"),
            risk_tolerance=data.get("risk_tolerance"),
            phase=phase,
            survey_completed=True,
        )

    income = data.get("monthly_income", 0) or 0
    expenses = data.get("monthly_expenses", 0) or 0
    sr = ((income - expenses) / income * 100) if income > 0 else 0
    debts = data.get("debts", 0) or 0
    dti = (debts / income * 100) if income > 0 else 0
    sr_emoji = "✅" if sr >= 30 else "⚠️" if sr >= 15 else "🚨"
    dti_emoji = "✅" if dti < 20 else "⚠️" if dti < 40 else "🚨"

    from templates.messages import PHASE_NAMES
    phase_str = PHASE_NAMES.get(phase, phase)

    await callback.message.answer(
        SURVEY_DONE.format(
            sr=f"{sr:.1f}%",
            sr_emoji=sr_emoji,
            dti=f"{dti:.1f}%",
            dti_emoji=dti_emoji,
            phase=phase_str,
        ),
        reply_markup=main_menu(),
    )
    await callback.answer()
