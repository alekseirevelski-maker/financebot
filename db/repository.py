from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from db.engine import async_session
from db.models import User, Transaction, Reminder, RecurringPayment, SavingsGoal, Budget
from utils.timezone import now as tz_now


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, user_id: int, full_name: str, username: str | None = None) -> User:
        user = User(id=user_id, full_name=full_name, username=username, phase="learning")
        self.session.add(user)
        await self.session.commit()
        return user

    async def get_or_create(self, user_id: int, full_name: str, username: str | None = None) -> User:
        user = await self.get(user_id)
        if user:
            return user
        return await self.create(user_id, full_name, username)

    async def update(self, user_id: int, **kwargs) -> None:
        user = await self.get(user_id)
        if user:
            for key, value in kwargs.items():
                setattr(user, key, value)
            user.updated_at = tz_now()
            await self.session.commit()

    async def get_all(self) -> list[User]:
        result = await self.session.execute(select(User))
        return list(result.scalars().all())


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: int, type_: str, amount: float, category: str, description: str | None = None, source: str | None = None) -> Transaction:
        tx = Transaction(user_id=user_id, type=type_, amount=amount, category=category, description=description, source=source)
        self.session.add(tx)
        await self.session.commit()
        return tx

    async def get_month_stats(self, user_id: int) -> dict:
        now = tz_now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(Transaction).where(Transaction.user_id == user_id, Transaction.date >= start)
        )
        txs = list(result.scalars().all())
        income = sum(t.amount for t in txs if t.type == "income")
        expense = sum(t.amount for t in txs if t.type == "expense")
        invest = sum(t.amount for t in txs if t.type == "investment")
        return {"income": income, "expense": expense, "investment": invest, "count": len(txs)}

    async def get_week_stats(self, user_id: int) -> dict:
        start = tz_now() - timedelta(days=7)
        result = await self.session.execute(
            select(Transaction).where(Transaction.user_id == user_id, Transaction.date >= start)
        )
        txs = list(result.scalars().all())
        income = sum(t.amount for t in txs if t.type == "income")
        expense = sum(t.amount for t in txs if t.type == "expense")
        invest = sum(t.amount for t in txs if t.type == "investment")
        return {"income": income, "expense": expense, "investment": invest, "count": len(txs)}

    async def get_today_stats(self, user_id: int) -> dict:
        now = tz_now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.date >= start,
            ).order_by(Transaction.date.desc())
        )
        txs = list(result.scalars().all())
        income = sum(t.amount for t in txs if t.type == "income")
        expense = sum(t.amount for t in txs if t.type == "expense")
        return {"income": income, "expense": expense, "count": len(txs), "txs": txs}

    async def get_all_csv(self, user_id: int) -> list[Transaction]:
        result = await self.session.execute(
            select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date)
        )
        return list(result.scalars().all())

    async def delete_last(self, user_id: int) -> Transaction | None:
        result = await self.session.execute(
            select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date.desc()).limit(1)
        )
        tx = result.scalar_one_or_none()
        if tx:
            await self.session.delete(tx)
            await self.session.commit()
        return tx

    async def get_expenses_by_category(self, user_id: int, months: int = 1) -> dict[str, float]:
        now = tz_now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if months > 1:
            start = start - timedelta(days=30 * (months - 1))
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.date >= start,
            )
        )
        txs = list(result.scalars().all())
        by_cat = {}
        for tx in txs:
            by_cat[tx.category] = by_cat.get(tx.category, 0) + tx.amount
        return dict(sorted(by_cat.items(), key=lambda x: x[1], reverse=True))

    async def get_monthly_totals(self, user_id: int, months: int = 6) -> list[dict]:
        now = tz_now()
        results = []
        for i in range(months - 1, -1, -1):
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month + 1, 1)
            result = await self.session.execute(
                select(Transaction).where(
                    Transaction.user_id == user_id,
                    Transaction.date >= start,
                    Transaction.date < end,
                )
            )
            txs = list(result.scalars().all())
            income = sum(t.amount for t in txs if t.type == "income")
            expense = sum(t.amount for t in txs if t.type == "expense")
            invest = sum(t.amount for t in txs if t.type == "investment")
            results.append({
                "month": f"{year}-{month:02d}",
                "income": income,
                "expense": expense,
                "investment": invest,
            })
        return results

    async def get_savings_rate_history(self, user_id: int, months: int = 6) -> list[tuple[str, float]]:
        monthly = await self.get_monthly_totals(user_id, months)
        history = []
        for m in monthly:
            if m["income"] > 0:
                sr = (m["income"] - m["expense"]) / m["income"] * 100
            else:
                sr = 0
            history.append((m["month"], sr))
        return history

    async def get_comparison_data(self, user_id: int) -> dict:
        now = tz_now()
        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 1:
            prev_start = datetime(now.year - 1, 12, 1)
        else:
            prev_start = datetime(now.year, now.month - 1, 1)
        current_end = datetime(now.year, now.month + 1, 1) if now.month < 12 else datetime(now.year + 1, 1, 1)

        async def _stats(start, end):
            result = await self.session.execute(
                select(Transaction).where(
                    Transaction.user_id == user_id,
                    Transaction.date >= start,
                    Transaction.date < end,
                )
            )
            txs = list(result.scalars().all())
            return {
                "income": sum(t.amount for t in txs if t.type == "income"),
                "expense": sum(t.amount for t in txs if t.type == "expense"),
                "investment": sum(t.amount for t in txs if t.type == "investment"),
                "count": len(txs),
            }

        return {
            "current": await _stats(current_start, current_end),
            "previous": await _stats(prev_start, current_start),
        }


class RecurringRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: int, name: str, amount: float, category: str, day_of_month: int) -> RecurringPayment:
        rp = RecurringPayment(user_id=user_id, name=name, amount=amount, category=category, day_of_month=day_of_month)
        self.session.add(rp)
        await self.session.commit()
        return rp

    async def get_active(self, user_id: int) -> list[RecurringPayment]:
        result = await self.session.execute(
            select(RecurringPayment).where(
                RecurringPayment.user_id == user_id,
                RecurringPayment.is_active == True,
            ).order_by(RecurringPayment.day_of_month)
        )
        return list(result.scalars().all())

    async def delete(self, user_id: int, payment_id: int) -> bool:
        result = await self.session.execute(
            select(RecurringPayment).where(
                RecurringPayment.id == payment_id,
                RecurringPayment.user_id == user_id,
            )
        )
        rp = result.scalar_one_or_none()
        if rp:
            rp.is_active = False
            await self.session.commit()
            return True
        return False

    async def get_monthly_total(self, user_id: int) -> float:
        active = await self.get_active(user_id)
        return sum(rp.amount for rp in active)

    async def get_today_payments(self, user_id: int) -> list[RecurringPayment]:
        today = tz_now().day
        active = await self.get_active(user_id)
        return [rp for rp in active if rp.day_of_month == today]

    async def process_today(self, user_id: int) -> list[Transaction]:
        today_payments = await self.get_today_payments(user_id)
        created = []
        for rp in today_payments:
            tx = Transaction(
                user_id=user_id, type="expense", amount=rp.amount,
                category=rp.category, description=rp.name, source="recurring",
            )
            self.session.add(tx)
            created.append(tx)
        if created:
            await self.session.commit()
        return created


class ReminderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active(self, user_id: int) -> list[Reminder]:
        result = await self.session.execute(
            select(Reminder).where(Reminder.user_id == user_id, Reminder.is_active == True)
        )
        return list(result.scalars().all())

    async def set(self, user_id: int, reminder_type: str, time_of_day: str) -> Reminder:
        existing = await self.session.execute(
            select(Reminder).where(Reminder.user_id == user_id, Reminder.reminder_type == reminder_type)
        )
        rem = existing.scalar_one_or_none()
        if rem:
            rem.time_of_day = time_of_day
            rem.is_active = True
        else:
            rem = Reminder(user_id=user_id, reminder_type=reminder_type, time_of_day=time_of_day)
            self.session.add(rem)
        await self.session.commit()
        return rem

    async def remove(self, user_id: int, reminder_type: str) -> None:
        result = await self.session.execute(
            select(Reminder).where(Reminder.user_id == user_id, Reminder.reminder_type == reminder_type)
        )
        rem = result.scalar_one_or_none()
        if rem:
            rem.is_active = False
            await self.session.commit()

    async def get_all_active_users(self) -> list[Reminder]:
        result = await self.session.execute(select(Reminder).where(Reminder.is_active == True))
        return list(result.scalars().all())


class SavingsGoalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: int, name: str, target_amount: float, deadline: str | None = None) -> SavingsGoal:
        goal = SavingsGoal(user_id=user_id, name=name, target_amount=target_amount, deadline=deadline)
        self.session.add(goal)
        await self.session.commit()
        return goal

    async def get_active(self, user_id: int) -> list[SavingsGoal]:
        result = await self.session.execute(
            select(SavingsGoal).where(
                SavingsGoal.user_id == user_id,
                SavingsGoal.is_completed == False,
            ).order_by(SavingsGoal.created_at)
        )
        return list(result.scalars().all())

    async def get_all(self, user_id: int) -> list[SavingsGoal]:
        result = await self.session.execute(
            select(SavingsGoal).where(SavingsGoal.user_id == user_id).order_by(SavingsGoal.created_at)
        )
        return list(result.scalars().all())

    async def update_amount(self, goal_id: int, user_id: int, add_amount: float) -> SavingsGoal | None:
        result = await self.session.execute(
            select(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id)
        )
        goal = result.scalar_one_or_none()
        if goal:
            goal.current_amount += add_amount
            if goal.current_amount >= goal.target_amount:
                goal.is_completed = True
            await self.session.commit()
        return goal

    async def delete(self, goal_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            select(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id)
        )
        goal = result.scalar_one_or_none()
        if goal:
            await self.session.delete(goal)
            await self.session.commit()
            return True
        return False

    async def get_total_progress(self, user_id: int) -> dict:
        goals = await self.get_active(user_id)
        total_target = sum(g.target_amount for g in goals)
        total_saved = sum(g.current_amount for g in goals)
        pct = (total_saved / total_target * 100) if total_target > 0 else 0
        return {"total_target": total_target, "total_saved": total_saved, "pct": pct, "count": len(goals)}


class BudgetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def set_budget(self, user_id: int, category: str, monthly_limit: float) -> Budget:
        existing = await self.session.execute(
            select(Budget).where(Budget.user_id == user_id, Budget.category == category, Budget.is_active == True)
        )
        budget = existing.scalar_one_or_none()
        if budget:
            budget.monthly_limit = monthly_limit
        else:
            budget = Budget(user_id=user_id, category=category, monthly_limit=monthly_limit)
            self.session.add(budget)
        await self.session.commit()
        return budget

    async def get_budgets(self, user_id: int) -> list[Budget]:
        result = await self.session.execute(
            select(Budget).where(Budget.user_id == user_id, Budget.is_active == True)
        )
        return list(result.scalars().all())

    async def get_budget(self, user_id: int, category: str) -> Budget | None:
        result = await self.session.execute(
            select(Budget).where(Budget.user_id == user_id, Budget.category == category, Budget.is_active == True)
        )
        return result.scalar_one_or_none()

    async def delete_budget(self, budget_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
        )
        budget = result.scalar_one_or_none()
        if budget:
            budget.is_active = False
            await self.session.commit()
            return True
        return False

    async def get_spending_vs_budget(self, user_id: int) -> list[dict]:
        budgets = await self.get_budgets(user_id)
        now = tz_now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.date >= start,
            )
        )
        txs = list(result.scalars().all())
        spent_by_cat = {}
        for tx in txs:
            spent_by_cat[tx.category] = spent_by_cat.get(tx.category, 0) + tx.amount

        report = []
        for b in budgets:
            spent = spent_by_cat.get(b.category, 0)
            remaining = b.monthly_limit - spent
            pct = (spent / b.monthly_limit * 100) if b.monthly_limit > 0 else 0
            status = "ok" if pct < 80 else "warning" if pct < 100 else "over"
            report.append({
                "category": b.category,
                "limit": b.monthly_limit,
                "spent": spent,
                "remaining": remaining,
                "pct": pct,
                "status": status,
            })
        return report
