from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None]
    full_name: Mapped[str]
    age: Mapped[int | None]
    profession: Mapped[str | None]
    monthly_income: Mapped[float | None]
    monthly_expenses: Mapped[float | None]
    assets: Mapped[float | None]
    debts: Mapped[float | None]
    free_hours: Mapped[float | None]
    investment_capital: Mapped[float | None]
    skills: Mapped[str | None]
    financial_goal: Mapped[str | None]
    goal_amount: Mapped[float | None]
    risk_tolerance: Mapped[str | None]
    phase: Mapped[str]
    survey_completed: Mapped[bool] = mapped_column(default=False)
    plan_generated: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.utcnow())
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.utcnow())


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int]
    type: Mapped[str]
    amount: Mapped[float]
    category: Mapped[str]
    description: Mapped[str | None]
    source: Mapped[str | None]
    date: Mapped[datetime] = mapped_column(default=lambda: datetime.utcnow())


class RecurringPayment(Base):
    __tablename__ = "recurring_payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int]
    name: Mapped[str]
    amount: Mapped[float]
    category: Mapped[str]
    day_of_month: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.utcnow())


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int]
    reminder_type: Mapped[str]
    time_of_day: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int]
    name: Mapped[str]
    target_amount: Mapped[float]
    current_amount: Mapped[float] = mapped_column(default=0.0)
    deadline: Mapped[str | None]
    is_completed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.utcnow())


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int]
    category: Mapped[str]
    monthly_limit: Mapped[float]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.utcnow())
