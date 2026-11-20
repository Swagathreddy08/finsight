from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummary,
    CategorySpending,
    CurrencySummary,
)


def spending_summary(
    db: Session,
    user: User,
    start_date: date | None,
    end_date: date | None,
) -> AnalyticsSummary:
    today = date.today()
    resolved_end = end_date or today
    resolved_start = start_date or (resolved_end - timedelta(days=29))
    if resolved_start > resolved_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be on or before end_date",
        )

    filters = (
        Transaction.user_id == user.id,
        Transaction.transaction_date >= resolved_start,
        Transaction.transaction_date <= resolved_end,
    )
    totals = db.execute(
        select(
            Transaction.currency,
            func.count(Transaction.id),
            func.coalesce(
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)),
                0,
            ),
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .where(*filters)
        .group_by(Transaction.currency)
        .order_by(Transaction.currency)
    ).all()

    category_rows = db.execute(
        select(
            Transaction.currency,
            Transaction.category,
            func.sum(-Transaction.amount),
        )
        .where(*filters, Transaction.amount < 0)
        .group_by(Transaction.currency, Transaction.category)
        .order_by(Transaction.currency, func.sum(-Transaction.amount).desc())
    ).all()
    categories_by_currency: dict[str, list[CategorySpending]] = {}
    for currency, category, amount in category_rows:
        categories_by_currency.setdefault(currency, []).append(
            CategorySpending(category=category or "Uncategorized", amount=Decimal(amount))
        )

    return AnalyticsSummary(
        start_date=resolved_start,
        end_date=resolved_end,
        currency_summaries=[
            CurrencySummary(
                currency=currency,
                transaction_count=count,
                income=Decimal(income),
                expenses=Decimal(expenses),
                net=Decimal(net),
                spending_by_category=categories_by_currency.get(currency, []),
            )
            for currency, count, income, expenses, net in totals
        ],
    )
