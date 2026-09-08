"""PDF report generation service."""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from utils.timezone import now as tz_now


def generate_monthly_report(user_data: dict, tx_stats: dict, budget_data: list, savings_data: dict) -> io.BytesIO:
    """Generate a monthly PDF report."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2*cm, height - 3*cm, "Financial Report")
    c.setFont("Helvetica", 12)
    c.drawString(2*cm, height - 4*cm, f"Month: {tz_now().strftime('%B %Y')}")

    # Summary
    y = height - 6*cm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, y, "Summary")
    y -= 1*cm
    c.setFont("Helvetica", 11)

    items = [
        (f"Income: {tx_stats.get('income', 0):,.0f} RUB", colors.green),
        (f"Expenses: {tx_stats.get('expense', 0):,.0f} RUB", colors.red),
        (f"Investments: {tx_stats.get('investment', 0):,.0f} RUB", colors.blue),
    ]
    for text, color in items:
        c.setFillColor(color)
        c.drawString(3*cm, y, text)
        y -= 0.6*cm

    net = tx_stats.get('income', 0) - tx_stats.get('expense', 0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(3*cm, y, f"Net: {net:,.0f} RUB")
    y -= 1.5*cm

    # Budget section
    if budget_data:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(2*cm, y, "Budget vs Actual")
        y -= 1*cm
        c.setFont("Helvetica", 10)
        for b in budget_data:
            status = "OK" if b["status"] == "ok" else "WARN" if b["status"] == "warning" else "OVER"
            c.drawString(3*cm, y, f"{b['category']}: {b['spent']:,.0f}/{b['limit']:,.0f} ({status})")
            y -= 0.5*cm
            if y < 5*cm:
                c.showPage()
                y = height - 3*cm

    # Savings section
    if savings_data and savings_data.get("count", 0) > 0:
        y -= 1*cm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(2*cm, y, "Savings Goals")
        y -= 1*cm
        c.setFont("Helvetica", 11)
        c.drawString(3*cm, y, f"Total: {savings_data.get('total_saved', 0):,.0f} / {savings_data.get('total_target', 0):,.0f} ({savings_data.get('pct', 0):.0f}%)")

    c.save()
    buf.seek(0)
    return buf


def generate_weekly_report(user_data: dict, tx_stats: dict) -> io.BytesIO:
    """Generate a weekly PDF report."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(2*cm, height - 3*cm, "Weekly Report")
    c.setFont("Helvetica", 12)
    now = tz_now()
    week_start = now - __import__('datetime').timedelta(days=now.weekday())
    c.drawString(2*cm, height - 4*cm, f"{week_start.strftime('%d.%m')} - {now.strftime('%d.%m.%Y')}")

    y = height - 6*cm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, y, "Summary")
    y -= 1*cm
    c.setFont("Helvetica", 11)

    net = tx_stats.get('income', 0) - tx_stats.get('expense', 0)
    c.drawString(3*cm, y, f"Income: {tx_stats.get('income', 0):,.0f} RUB")
    y -= 0.6*cm
    c.drawString(3*cm, y, f"Expenses: {tx_stats.get('expense', 0):,.0f} RUB")
    y -= 0.6*cm
    c.drawString(3*cm, y, f"Net: {net:,.0f} RUB")

    c.save()
    buf.seek(0)
    return buf
