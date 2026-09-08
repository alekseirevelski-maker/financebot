from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from db.engine import async_session
from db.repository import UserRepository
from keyboards.inline import main_menu
from templates.messages import WELCOME_NEW, WELCOME_BACK, MAIN_MENU_TEXT, HELP_TEXT

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    async with async_session() as session:
        repo = UserRepository(session)
        user = await repo.get_or_create(
            user_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
        )
    if user.survey_completed:
        await message.answer(
            WELCOME_BACK.format(name=user.full_name),
            reply_markup=main_menu(),
        )
    else:
        await message.answer(
            WELCOME_NEW.format(name=message.from_user.first_name),
            reply_markup=main_menu(),
        )


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.answer(MAIN_MENU_TEXT, reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help(callback: CallbackQuery):
    await callback.message.answer(HELP_TEXT)
    await callback.answer()


@router.callback_query(F.data == "menu:photo")
async def cb_photo(callback: CallbackQuery):
    await callback.message.answer(
        "📸 Отправь мне фото чека, скриншот банковского приложения или выписку.\n\n"
        "Я распознаю сумму, магазин, дату и категорию.\n"
        "Потом ты подтвердишь или поправишь перед сохранением."
    )
    await callback.answer()


@router.callback_query(F.data == "menu:today")
async def cb_today(callback: CallbackQuery):
    from handlers.tracker import cmd_today
    await cmd_today(callback.message)
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT)


@router.callback_query(F.data == "menu:budget")
async def cb_budget(callback: CallbackQuery):
    from handlers.budget import cmd_budget
    await cmd_budget(callback)
    await callback.answer()


@router.callback_query(F.data == "menu:savings")
async def cb_savings(callback: CallbackQuery):
    from handlers.savings import cmd_savings
    await cmd_savings(callback)
    await callback.answer()


@router.callback_query(F.data == "menu:analytics")
async def cb_analytics(callback: CallbackQuery):
    from handlers.analytics import cmd_analytics
    await cmd_analytics(callback)
    await callback.answer()


@router.callback_query(F.data == "menu:reports")
async def cb_reports(callback: CallbackQuery):
    from handlers.reports import cmd_report
    await cmd_report(callback)
    await callback.answer()


@router.callback_query(F.data == "menu:forecast")
async def cb_forecast(callback: CallbackQuery):
    from handlers.forecast import cmd_forecast
    await cmd_forecast(callback)
    await callback.answer()
