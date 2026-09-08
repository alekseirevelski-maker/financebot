import math


def savings_rate(income: float, expenses: float) -> float:
    if income <= 0:
        return 0.0
    return (income - expenses) / income * 100


def dti_ratio(debts: float, income: float) -> float:
    if income <= 0:
        return 100.0
    return debts / income * 100


def financial_buffer(assets: float, debts: float) -> float:
    return assets - debts


def months_without_income(assets: float, expenses: float) -> float:
    if expenses <= 0:
        return 999.0
    return assets / expenses


def investment_readiness(capital: float, income: float) -> float:
    if income <= 0:
        return 0.0
    return capital / income


def compound_future_value(pmt: float, annual_rate: float, months: int) -> dict:
    if annual_rate <= 0:
        total = pmt * months
        return {"future_value": total, "invested": total, "profit": 0}
    r = annual_rate / 100 / 12
    fv = pmt * ((1 + r) ** months - 1) / r
    invested = pmt * months
    profit = fv - invested
    return {"future_value": round(fv, 2), "invested": round(invested, 2), "profit": round(profit, 2)}


def months_to_target(savings_per_month: float, target: float, annual_rate: float = 0.0) -> int:
    if savings_per_month <= 0:
        return 9999
    if annual_rate <= 0:
        return math.ceil(target / savings_per_month)
    r = annual_rate / 100 / 12
    if r <= 0:
        return math.ceil(target / savings_per_month)
    months = math.ceil(math.log((target * r / savings_per_month) + 1) / math.log(1 + r))
    return max(1, months)


def risk_assessment(risk_tolerance: str, age: int | None, debts: float, income: float) -> str:
    dti = dti_ratio(debts, income)
    if dti > 50:
        return "high"
    if risk_tolerance == "high" and dti < 20:
        return "high"
    if risk_tolerance == "low" or age and age > 50:
        return "low"
    return "medium"


def progress_bar(current: float, target: float, length: int = 10) -> str:
    if target <= 0:
        return "▓" * length
    pct = min(current / target, 1.0)
    filled = round(pct * length)
    return "▓" * filled + "░" * (length - filled)


def format_currency(amount: float) -> str:
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f}M₽"
    if amount >= 1_000:
        return f"{amount / 1_000:.0f}K₽"
    return f"{amount:.0f}₽"
