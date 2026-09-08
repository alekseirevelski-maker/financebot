"""Financial forecasting engine."""

from datetime import datetime


def project_end_of_month(
    current_balance: float,
    daily_income: float,
    daily_expenses: float,
    days_remaining: int,
    recurring_monthly: float,
) -> dict:
    """Project balance at end of month."""
    daily_recurring = recurring_monthly / 30
    net_daily = daily_income - daily_expenses - daily_recurring
    projected = current_balance + (net_daily * days_remaining)
    return {
        "projected_balance": round(projected, 2),
        "net_daily": round(net_daily, 2),
        "days_remaining": days_remaining,
    }


def calculate_runway(
    current_balance: float,
    monthly_expenses: float,
    monthly_income: float = 0,
) -> dict:
    """How many months until broke (or positive cashflow)."""
    net_monthly_burn = monthly_expenses - monthly_income
    if net_monthly_burn <= 0:
        return {
            "months_to_zero": 999,
            "net_monthly_burn": round(net_monthly_burn, 2),
            "status": "positive_cashflow",
        }
    months_to_zero = current_balance / net_monthly_burn
    return {
        "months_to_zero": round(months_to_zero, 1),
        "net_monthly_burn": round(net_monthly_burn, 2),
        "status": "burning" if months_to_zero < 12 else "stable",
    }


def savings_trajectory(
    current_savings: float,
    monthly_savings: float,
    months: int = 12,
    annual_rate: float = 0.0,
) -> list[dict]:
    """Project savings growth over N months with optional compound interest."""
    trajectory = []
    balance = current_savings
    r = annual_rate / 100 / 12 if annual_rate > 0 else 0
    for m in range(1, months + 1):
        balance = balance * (1 + r) + monthly_savings
        trajectory.append({
            "month": m,
            "balance": round(balance, 2),
            "invested": round(current_savings + monthly_savings * m, 2),
        })
    return trajectory


def format_runway(runway: dict) -> str:
    """Format runway result as text."""
    if runway["status"] == "positive_cashflow":
        return "✅ Положительный денежный поток!\nДоходы превышают расходы.\nТраты не превышают доходы — можно инвестировать."
    months = runway["months_to_zero"]
    if months < 3:
        emoji = "🚨"
        warning = "КРИТИЧНО!"
    elif months < 6:
        emoji = "⚠️"
        warning = "Внимание!"
    elif months < 12:
        emoji = "📋"
        warning = ""
    else:
        emoji = "✅"
        warning = ""

    text = f"{emoji} {warning}\n" if warning else f"{emoji} "
    text += f"Запас: {months} мес.\n"
    text += f"Сжигаем: {runway['net_monthly_burn']:,.0f} ₽/мес"
    return text


def format_trajectory(trajectory: list[dict]) -> str:
    """Format trajectory as text."""
    lines = ["📈 Прогноз накоплений:\n"]
    for t in trajectory:
        lines.append(f"  Мес {t['month']:>2}: {t['balance']:>12,.0f} ₽ (вложено: {t['invested']:>12,.0f} ₽)")
    return "\n".join(lines)
