"""Generate financial charts as PNG images for Telegram."""

import io
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams['font.family'] = 'DejaVu Sans'

COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
          '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
          '#F8C471', '#82E0AA', '#F1948A']


def expense_pie_chart(category_data: dict[str, float]) -> io.BytesIO:
    """Pie chart: expense breakdown by category."""
    fig, ax = plt.subplots(figsize=(8, 6))
    labels = list(category_data.keys())
    sizes = list(category_data.values())
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct='%1.1f%%',
        colors=COLORS[:len(labels)], startangle=90
    )
    ax.set_title('Расходы по категориям', fontsize=14, fontweight='bold')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


def income_vs_expenses_bar(monthly_data: list[dict]) -> io.BytesIO:
    """Bar chart: income vs expenses over months."""
    fig, ax = plt.subplots(figsize=(10, 6))
    months = [m["month"] for m in monthly_data]
    income = [m["income"] for m in monthly_data]
    expense = [m["expense"] for m in monthly_data]

    x = range(len(months))
    width = 0.35
    ax.bar([i - width/2 for i in x], income, width, label='Доходы', color='#4ECDC4')
    ax.bar([i + width/2 for i in x], expense, width, label='Расходы', color='#FF6B6B')

    ax.set_xlabel('Месяц')
    ax.set_ylabel('Сумма (₽)')
    ax.set_title('Доходы vs Расходы', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=45)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


def monthly_trend_line(monthly_data: list[dict]) -> io.BytesIO:
    """Line chart: monthly income/expense/investment trend."""
    fig, ax = plt.subplots(figsize=(10, 6))
    months = [m["month"] for m in monthly_data]

    ax.plot(months, [m["income"] for m in monthly_data], marker='o', label='Доходы', color='#4ECDC4', linewidth=2)
    ax.plot(months, [m["expense"] for m in monthly_data], marker='s', label='Расходы', color='#FF6B6B', linewidth=2)
    ax.plot(months, [m["investment"] for m in monthly_data], marker='^', label='Инвестиции', color='#45B7D1', linewidth=2)

    ax.set_xlabel('Месяц')
    ax.set_ylabel('Сумма (₽)')
    ax.set_title('Тренд по месяцам', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.tick_params(axis='x', rotation=45)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


def top_categories_bar(category_data: dict[str, float], top_n: int = 5) -> io.BytesIO:
    """Horizontal bar chart: top N spending categories."""
    fig, ax = plt.subplots(figsize=(8, 5))
    items = list(category_data.items())[:top_n]
    labels = [x[0] for x in items]
    values = [x[1] for x in items]

    bars = ax.barh(labels[::-1], values[::-1], color=COLORS[:len(labels)])
    ax.set_xlabel('Сумма (₽)')
    ax.set_title(f'Топ-{top_n} категорий расходов', fontsize=14, fontweight='bold')

    for bar, val in zip(bars, values[::-1]):
        ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height()/2,
                f'{val:,.0f}₽', va='center', fontsize=10)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


def savings_rate_timeline(sr_data: list[tuple[str, float]]) -> io.BytesIO:
    """Line chart: savings rate over time."""
    fig, ax = plt.subplots(figsize=(10, 6))
    months = [x[0] for x in sr_data]
    rates = [x[1] for x in sr_data]

    ax.plot(months, rates, marker='o', color='#4ECDC4', linewidth=2, label='Норма сбережений')
    ax.axhline(y=30, color='#4ECDC4', linestyle='--', alpha=0.5, label='Цель: 30%')
    ax.axhline(y=15, color='#FFEAA7', linestyle='--', alpha=0.5, label='Минимум: 15%')
    ax.fill_between(months, rates, alpha=0.2, color='#4ECDC4')

    ax.set_xlabel('Месяц')
    ax.set_ylabel('%')
    ax.set_title('Норма сбережений по месяцам', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.tick_params(axis='x', rotation=45)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


def forecast_trajectory(trajectory: list[dict]) -> io.BytesIO:
    """Line chart: savings trajectory forecast."""
    fig, ax = plt.subplots(figsize=(10, 6))
    months = [f"Мес {t['month']}" for t in trajectory]
    balances = [t["balance"] for t in trajectory]
    invested = [t["invested"] for t in trajectory]

    ax.plot(months, balances, marker='o', color='#4ECDC4', linewidth=2, label='Баланс (с %)')
    ax.plot(months, invested, marker='s', color='#FF6B6B', linewidth=2, linestyle='--', label='Без %')

    ax.set_xlabel('Месяц')
    ax.set_ylabel('Сумма (₽)')
    ax.set_title('Прогноз накоплений', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.tick_params(axis='x', rotation=45)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf
