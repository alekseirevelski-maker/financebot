from db.models import User
from services.calculator import (
    savings_rate, dti_ratio, months_to_target, format_currency, progress_bar
)
from services.income_ideas import SKILL_BASED, AI_BASED, ONLINE, DIGITAL_ASSETS, SCALABLE
from services.strategies import STRATEGIES, THINKER_NAMES
from templates.messages import PLAN_HEADERS

THRESHOLDS = [170_000, 850_000, 1_700_000, 8_500_000, 17_000_000]


def generate_plan(user: User) -> list[str]:
    income = user.monthly_income or 0
    expenses = user.monthly_expenses or 0
    assets = user.assets or 0
    debts = user.debts or 0
    capital = user.investment_capital or 0
    goal_amount = user.goal_amount or 1_000_000
    skills = user.skills or ""
    phase = user.phase or "learning"

    sr = savings_rate(income, expenses)
    dti = dti_ratio(debts, income)
    net = income - expenses

    sections = []
    sections.append(_diagnostics(user, sr, dti, net))
    sections.append(_capital_map(user, sr, net))
    sections.append(_accumulation_strategy(user, net))
    sections.append(_income_machine(user))
    sections.append(_implementation_plan(user, net))
    sections.append(_critical_errors(user, sr, dti))
    sections.append(_millionaire_mindset(user))
    return sections


def _diagnostics(user, sr, dti, net):
    income = user.monthly_income or 0
    assets = user.assets or 0
    debts = user.debts or 0
    capital = user.investment_capital or 0

    sr_emoji = "✅" if sr >= 30 else "⚠️" if sr >= 15 else "🚨"
    dti_emoji = "✅" if dti < 20 else "⚠️" if dti < 40 else "🚨"
    buf = assets - debts
    months_runway = (assets / (user.monthly_expenses or 1)) if user.monthly_expenses else 999

    skills_list = [s.strip() for s in (user.skills or "").split(",") if s.strip()]
    top_skills = skills_list[:3] if skills_list else ["не указаны"]

    strengths = []
    weaknesses = []
    if sr >= 20:
        strengths.append("Хороший savings rate")
    else:
        weaknesses.append("Низкий savings rate")
    if assets > debts:
        strengths.append("Положительный баланс")
    else:
        weaknesses.append("Долги превышают активы")
    if capital > 0:
        strengths.append("Есть инвестиционный капитал")
    else:
        weaknesses.append("Нет инвестиционного капитала")
    if user.free_hours and user.free_hours >= 2:
        strengths.append("Достаточно свободного времени")
    if len(skills_list) >= 3:
        strengths.append("Разнообразные навыки")
    if not strengths:
        strengths = ["Есть желание изменить ситуацию"]

    return (
        f"{PLAN_HEADERS[0]}\n\n"
        f"📊 Финансовые метрики:\n"
        f"• Savings Rate: {sr:.1f}% {sr_emoji}\n"
        f"• DTI: {dti:.1f}% {dti_emoji}\n"
        f"• Чистый доход: {format_currency(net)}/мес\n"
        f"• Финансовый буфер: {format_currency(buf)}\n"
        f"• Запас без дохода: {months_runway:.0f} мес\n"
        f"• Инвестиционный капитал: {format_currency(capital)}\n\n"
        f"💪 Сильные стороны:\n" + "\n".join(f"  • {s}" for s in strengths[:5]) +
        f"\n\n⚠️ Слабые стороны:\n" + "\n".join(f"  • {w}" for w in weaknesses[:5]) +
        f"\n\n🎯 Pareto 80/20 — твои 20%:\n"
        f"  1. Увеличь savings rate до 30%+\n"
        f"  2. Развивай 1-2 навыка для доп. дохода\n"
        f"  3. Начни инвестировать хотя бы 10% от дохода"
    )


def _capital_map(user, sr, net):
    income = user.monthly_income or 0
    skills = user.skills or ""
    capital = user.investment_capital or 0

    quick_income = []
    if "фриланс" in skills.lower() or "разработ" in skills.lower():
        quick_income.append("Фриланс по навыкам (0-30 дней)")
    else:
        quick_income.append("Подработка по навыкам (0-30 дней)")
    quick_income.append("Продажа ненужных вещей (0-7 дней)")

    if income < 100_000:
        main_plan = "Ищи работу с доходом × 1.5-2 от текущего"
    elif income < 200_000:
        main_plan = "Переговоры о повышении или смена работодателя"
    else:
        main_plan = "Оптимизируй текущий доход, фокус на масштабировании"

    extra = "Консалтинг / менторство по навыкам (1-3 мес)"

    portfolio = []
    if capital > 0:
        portfolio.append("ETF индексные (30%)")
        portfolio.append("ОФЗ (40%)")
        portfolio.append("Золото ETF (7.5%)")
        portfolio.append("Товары (7.5%)")
        portfolio.append("Длинные облигации (15%)")
    else:
        portfolio.append("Начни с 1000₽/мес в индексный ETF")

    passive = "Дивидендные акции + ОФЗ (6-24 мес)"
    capital_plan = "Сложный процент: реинвестируй все доходы 2+ года"

    return (
        f"{PLAN_HEADERS[1]}\n\n"
        f"⚡ Быстрый доход (0-30 дней):\n" + "\n".join(f"  • {x}" for x in quick_income) +
        f"\n\n💼 Основной доход (1-6 мес):\n  • {main_plan}" +
        f"\n\n🔍 Доп. доход (1-3 мес):\n  • {extra}" +
        f"\n\n📈 Активы (3-12 мес):\n" + "\n".join(f"  • {x}" for x in portfolio) +
        f"\n\n💰 Регулярный доход (6-24 мес):\n  • {passive}" +
        f"\n\n🏦 Капитал (2+ года):\n  • {capital_plan}"
    )


def _accumulation_strategy(user, net):
    results = []
    for i, target in enumerate(THRESHOLDS):
        months = months_to_target(max(net, 1), target, 8.0)
        time_str = f"{months} мес ({months / 12:.1f} лет)" if months > 12 else f"{months} мес"
        results.append(
            f"  {i+1}. {format_currency(target)} — {time_str}\n"
            f"     Действия: {'→'.join(_threshold_actions(i))}\n"
            f"     Навыки: {', '.join(_threshold_skills(i))}"
        )

    return (
        f"{PLAN_HEADERS[2]}\n\n"
        f"Стратегия при {user.risk_tolerance or 'среднем'} риске:\n\n"
        + "\n\n".join(results)
    )


def _threshold_actions(level):
    actions = [
        ["Экономь 30%+", "Фриланс", "Контроль расходов"],
        ["Увеличь доход ×1.5", "Инвестируй 20%", "Создай запас"],
        ["Масштабируй бизнес", "Диверсифицируй", "Найми подрядчиков"],
        ["Системы > ручная работа", "Инвестируй в активы", "Цифровые продукты"],
        ["Фонд / пул", "Лицензирование", "Пассивный доход > расходы"],
    ]
    return actions[min(level, len(actions) - 1)]


def _threshold_skills(level):
    skills = [
        ["Экономика", "Дисциплина", "Фриланс"],
        ["Продажи", "Маркетинг", "Инвестиции"],
        ["Лидерство", "Финансовая грамотность", "Масштабирование"],
        ["Системное мышление", "Инвестиции", "Менторство"],
        ["Стратегия", "Филантропия", "Нетворкинг"],
    ]
    return skills[min(level, len(skills) - 1)]


def _income_machine(user):
    skills = user.skills or ""
    skill_keywords = [s.strip().lower() for s in skills.split(",") if s.strip()]

    def match_score(idea):
        name = idea["name"].lower()
        return sum(1 for kw in skill_keywords if kw in name or name.startswith(kw[:4]))

    top_skills = sorted(SKILL_BASED, key=match_score, reverse=True)[:5]
    top_ai = AI_BASED[:5]
    top_online = ONLINE[:5]
    top_digital = DIGITAL_ASSETS[:5]
    top_scale = SCALABLE[:5]

    return (
        f"{PLAN_HEADERS[3]}\n\n"
        f"💼 По твоим навыкам:\n{fmt_idea_list(top_skills)}\n\n"
        f"🤖 С помощью ИИ:\n{fmt_idea_list(top_ai)}\n\n"
        f"🌐 Онлайн:\n{fmt_idea_list(top_online)}\n\n"
        f"📱 Цифровые активы:\n{fmt_idea_list(top_digital)}\n\n"
        f"🚀 Масштабируемые:\n{fmt_idea_list(top_scale)}"
    )


def fmt_idea_list(items):
    return "\n".join(
        f"  • {i['name']} — {i['profit']} (окуп: {i['payback']}, сложность: {i['difficulty']}/5, масштаб: {i['scale']}/5)"
        for i in items
    )


def _implementation_plan(user, net):
    income = user.monthly_income or 0
    target_income = income * 2
    goal_amount = user.goal_amount or 1_000_000

    return (
        f"{PLAN_HEADERS[4]}\n\n"
        f"📅 30 дней — быстрые победы:\n"
        f"  1. Записывай все расходы 7 дней\n"
        f"  2. Выбери 1 источник доп. дохода\n"
        f"  3. Настроить ежедневное напоминание\n"
        f"  4. Прочитай 1 книгу: «Психология денег»\n"
        f"  5. Savings rate → +10%\n\n"
        f"📅 90 дней — стабильный рост:\n"
        f"  1. Запусти side project\n"
        f"  2. Начни инвестировать 10%+\n"
        f"  3. Освой 1 новый навык\n"
        f"  4. Доход → {format_currency(target_income)}/мес\n\n"
        f"📅 1 год — масштабирование:\n"
        f"  1. Доход × 2 от baseline\n"
        f"  2. Инвестиционный портфель сформирован\n"
        f"  3. 2+ источника дохода\n"
        f"  4. 1-й порог накопления: {format_currency(THRESHOLDS[0])}\n\n"
        f"📅 3 года — финансовая свобода:\n"
        f"  1. Целевой капитал: {format_currency(goal_amount)}\n"
        f"  2. Пассивный доход > расходы\n"
        f"  3. Системы работают без тебя\n"
        f"  4. Финансовая подушка 12+ мес"
    )


def _critical_errors(user, sr, dti):
    warnings = []
    if dti > 30:
        warnings.append("🚨 DTI > 30%: Сначала погаси долги! (Мунгер: инверсия — избегай того, что разрушает)")
    if sr < 15:
        warnings.append("⚠️ Savings rate < 15%: Хаузол — savings rate важнее дохода от инвестиций")
    if (user.investment_capital or 0) == 0 and (user.monthly_income or 0) > 0:
        warnings.append("⚠️ Нет инвестиций: инфляция 7% съедает 50% за 10 лет")
    if (user.assets or 0) < (user.monthly_expenses or 0) * 3:
        warnings.append("⚠️ Финансовая подушка < 3 мес: нужен запас на случай потери дохода")

    return (
        f"{PLAN_HEADERS[5]}\n\n"
        f"🚨 Твои предупреждения:\n" + "\n".join(f"  {w}" for w in warnings if warnings) +
        (f"\n\nВсё чисто! ✅" if not warnings else "") +
        f"\n\n📌 Типичные ловушки среднего класса:\n"
        f"  • Кредиты на потребление (авто, техника)\n"
        f"  • Ипотека > 30% от дохода\n"
        f"  • Нет фонда на 3-6 месяцев\n"
        f"  • Все деньги в одном активе\n"
        f"  • Инвестиции по совету «экспертов» из соцсетей\n\n"
        f"📌 Незаметные траты:\n"
        f"  • Подписки: ~5000₽/мес в среднем\n"
        f"  • Комиссии фондов: 1-2% годовых = 30% за 20 лет\n"
        f"  • Инфляция: 7% = деньги удешевляются в 2 раза за 10 лет\n\n"
        f"📌 Ограничивающие убеждения:\n"
        f"  • «Деньги — зло» → Баффет: деньги дают свободу выбора\n"
        f"  • «Инвестиции — риск» → Далио: диверсификация = бесплатный обед\n"
        f"  • «Нужно много денег» → Хаузол: начни с 1000₽\n"
        f"  • «Я не умею» → Навал: specific knowledge можно развить"
    )


def _millionaire_mindset(user):
    phase = user.phase or "learning"
    phase_strategies = {
        "learning": ["naval", "munger", "carnegie"],
        "earning": ["hormozi", "thiel", "buffett"],
        "investing": ["buffett", "dalio", "housel"],
        "scaling": ["thiel", "naval", "carnegie"],
        "preserving": ["housel", "dalio", "munger"],
    }
    relevant = phase_strategies.get(phase, ["buffett", "munger", "dalio"])

    blocks = []
    for key in relevant:
        s = STRATEGIES[key]
        principle = s["principles"][0]
        quote = s["quotes"][0]
        blocks.append(
            f"🧠 {s['name']}:\n"
            f"  Принцип: {principle}\n"
            f"  Цитата: {quote}"
        )

    return (
        f"{PLAN_HEADERS[6]}\n\n"
        f"Твоя фаза: {phase}\n"
        f"Релевантные мыслители:\n\n"
        + "\n\n".join(blocks) +
        f"\n\n💡 Ключевой принцип:\n"
        f"  Богатство = Specific Knowledge + Leverage + Time\n"
        f"  Начни сейчас. Терпение — твоя суперсила."
    )
