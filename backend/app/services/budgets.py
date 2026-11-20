from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.budgets import BudgetProgress


def month_end(month: date) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, 1) - timedelta(days=1)
    return date(month.year, month.month + 1, 1) - timedelta(days=1)


def budget_progress(
    db: Session,
    user: User,
    budgets: list[Budget],
) -> list[BudgetProgress]:
    if not budgets:
        return []
    month = budgets[0].month
    actual_rows = db.execute(
        select(
            Transaction.category,
            Transaction.currency,
            func.sum(-Transaction.amount),
        )
        .where(
            Transaction.user_id == user.id,
            Transaction.amount < 0,
            Transaction.transaction_date >= month,
            Transaction.transaction_date <= month_end(month),
        )
        .group_by(Transaction.category, Transaction.currency)
    ).all()
    actuals = {
        (category or "Uncategorized", currency): Decimal(amount)
        for category, currency, amount in actual_rows
    }
    results: list[BudgetProgress] = []
    for budget in budgets:
        spent = actuals.get((budget.category, budget.currency), Decimal("0.00"))
        results.append(
            BudgetProgress(
                id=budget.id,
                category=budget.category,
                currency=budget.currency,
                month=budget.month,
                budget_amount=budget.amount,
                spent=spent,
                remaining=budget.amount - spent,
                percent_used=(spent * 100 / budget.amount).quantize(Decimal("0.01")),
            )
        )
    return results


def list_budgets(db: Session, user: User, month: date) -> list[BudgetProgress]:
    budgets = list(
        db.scalars(
            select(Budget)
            .where(Budget.user_id == user.id, Budget.month == month)
            .order_by(Budget.currency, Budget.category)
        )
    )
    return budget_progress(db, user, budgets)
