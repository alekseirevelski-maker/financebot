from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Профиль", callback_data="menu:profile"),
            InlineKeyboardButton(text="📊 План", callback_data="menu:plan"),
        ],
        [
            InlineKeyboardButton(text="💹 Трекер", callback_data="menu:tracker"),
            InlineKeyboardButton(text="📸 Фото-чек", callback_data="menu:photo"),
        ],
        [
            InlineKeyboardButton(text="💳 Регулярные", callback_data="sub:list"),
            InlineKeyboardButton(text="📊 Сегодня", callback_data="menu:today"),
        ],
        [
            InlineKeyboardButton(text="📋 Бюджет", callback_data="menu:budget"),
            InlineKeyboardButton(text="🎯 Цели", callback_data="menu:savings"),
        ],
        [
            InlineKeyboardButton(text="📈 Аналитика", callback_data="menu:analytics"),
            InlineKeyboardButton(text="📄 Отчёты", callback_data="menu:reports"),
        ],
        [
            InlineKeyboardButton(text="🔮 Прогноз", callback_data="menu:forecast"),
            InlineKeyboardButton(text="🧠 Мудрость", callback_data="menu:wisdom"),
        ],
        [
            InlineKeyboardButton(text="🧮 Калькулятор", callback_data="menu:compound"),
            InlineKeyboardButton(text="⏰ Напоминания", callback_data="menu:reminders"),
        ],
        [
            InlineKeyboardButton(text="❓ Команды", callback_data="menu:help"),
        ],
    ])


def survey_start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать опрос", callback_data="survey:start")],
    ])


def risk_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Низкий", callback_data="risk:low"),
            InlineKeyboardButton(text="🟡 Средний", callback_data="risk:medium"),
            InlineKeyboardButton(text="🔴 Высокий", callback_data="risk:high"),
        ],
    ])


def phase_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Обучение", callback_data="phase:learning")],
        [InlineKeyboardButton(text="💼 Заработок", callback_data="phase:earning")],
        [InlineKeyboardButton(text="📈 Инвестиции", callback_data="phase:investing")],
        [InlineKeyboardButton(text="🚀 Масштабирование", callback_data="phase:scaling")],
        [InlineKeyboardButton(text="🏦 Сохранение", callback_data="phase:preserving")],
    ])


def plan_nav(current: int, total: int) -> InlineKeyboardMarkup:
    buttons = []
    if current > 0:
        buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"plan:{current - 1}"))
    buttons.append(InlineKeyboardButton(text=f"●{current + 1}/{total}●", callback_data="plan:noop"))
    if current < total - 1:
        buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"plan:{current + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[
        buttons,
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")],
    ])


def tracker_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Доход", callback_data="tracker:income"),
            InlineKeyboardButton(text="💸 Расход", callback_data="tracker:expense"),
        ],
        [
            InlineKeyboardButton(text="📈 Инвестиция", callback_data="tracker:invest"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="tracker:stats"),
        ],
        [
            InlineKeyboardButton(text="📁 Экспорт CSV", callback_data="tracker:export"),
        ],
        [
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
        ],
    ])


def reminders_keyboard(active: list[str]) -> InlineKeyboardMarkup:
    types = [
        ("daily", "☀️ Ежедневная проверка"),
        ("weekly", "📅 Еженедельный обзор"),
        ("wisdom", "🧠 Цитата дня"),
        ("plan_step", "🎯 Шаг плана"),
    ]
    buttons = []
    for rtype, label in types:
        status = "✅" if rtype in active else "⬜"
        buttons.append([InlineKeyboardButton(text=f"{status} {label}", callback_data=f"remind:{rtype}")])
    buttons.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def wisdom_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏛 Баффет", callback_data="wisdom:buffett"),
            InlineKeyboardButton(text="🧩 Мунгер", callback_data="wisdom:munger"),
        ],
        [
            InlineKeyboardButton(text="🌊 Далио", callback_data="wisdom:dalio"),
            InlineKeyboardButton(text="⚡ Равикант", callback_data="wisdom:naval"),
        ],
        [
            InlineKeyboardButton(text="📖 Хаузол", callback_data="wisdom:housel"),
            InlineKeyboardButton(text="🔥 Хормози", callback_data="wisdom:hormozi"),
        ],
        [
            InlineKeyboardButton(text="🎯 Тил", callback_data="wisdom:thiel"),
            InlineKeyboardButton(text="🏗 Карнеги", callback_data="wisdom:carnegie"),
        ],
        [
            InlineKeyboardButton(text="🎲 Случайная", callback_data="wisdom:random"),
        ],
        [
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
        ],
    ])


def update_keyboard() -> InlineKeyboardMarkup:
    fields = [
        ("🎂 Возраст", "update:age"),
        ("💼 Профессия", "update:profession"),
        ("💰 Доход", "update:monthly_income"),
        ("💸 Расходы", "update:monthly_expenses"),
        ("🏦 Активы", "update:assets"),
        ("📉 Долги", "update:debts"),
        ("🛠 Навыки", "update:skills"),
        ("🎯 Цель", "update:financial_goal"),
    ]
    buttons = []
    for i in range(0, len(fields), 2):
        row = [InlineKeyboardButton(text=name, callback_data=cb) for name, cb in fields[i:i+2]]
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def compound_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💡 5K × 12% × 5 лет", callback_data="compound:5000:12:60"),
            InlineKeyboardButton(text="💡 10K × 12% × 5 лет", callback_data="compound:10000:12:60"),
        ],
        [
            InlineKeyboardButton(text="💡 20K × 15% × 10 лет", callback_data="compound:20000:15:120"),
            InlineKeyboardButton(text="💡 50K × 12% × 10 лет", callback_data="compound:50000:12:120"),
        ],
        [
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
        ],
    ])


def photo_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data="photo:confirm"),
        ],
        [
            InlineKeyboardButton(text="💰 Сумма", callback_data="photo:edit_amount"),
            InlineKeyboardButton(text="🏷 Категория", callback_data="photo:edit_category"),
        ],
        [
            InlineKeyboardButton(text="📅 Дата", callback_data="photo:edit_date"),
            InlineKeyboardButton(text="🏪 Магазин", callback_data="photo:edit_merchant"),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="photo:cancel"),
        ],
    ])
