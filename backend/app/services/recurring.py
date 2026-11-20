from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.recurring import RecurringCharge, RecurringChargesResponse


def _months_ago(months: int, today: date) -> date:
    month_index = today.year * 12 + today.month - 1 - (months - 1)
    year, month = divmod(month_index, 12)
    return date(year, month + 1, 1)


def find_recurring_charges(
    db: Session,
    user: User,
    months: int,
) -> RecurringChargesResponse:
    today = date.today()
    start_date = _months_ago(months, today)
    transactions = db.scalars(
        select(Transaction)
        .where(
            Transaction.user_id == user.id,
            Transaction.amount < 0,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= today,
        )
        .order_by(Transaction.transaction_date)
    )

    groups: dict[tuple[str, str], list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        name = (transaction.merchant or transaction.description).strip()
        key = (transaction.currency, name.casefold())
        groups[key].append(transaction)

    charges: list[RecurringCharge] = []
    for (currency, _), entries in groups.items():
        if len(entries) < 3:
            continue
        recent = entries[-3:]
        intervals = [
            (recent[index].transaction_date - recent[index - 1].transaction_date).days
            for index in range(1, len(recent))
        ]
        if any(interval < 25 or interval > 35 for interval in intervals):
            continue

        amounts = [abs(Decimal(entry.amount)) for entry in recent]
        typical_amount = Decimal(str(median(amounts))).quantize(Decimal("0.01"))
        if max(amounts) - min(amounts) > typical_amount * Decimal("0.10"):
            continue

        latest = recent[-1]
        charges.append(
            RecurringCharge(
                name=latest.merchant or latest.description,
                currency=currency,
                typical_amount=typical_amount,
                category=latest.category,
                last_seen=latest.transaction_date,
                occurrences=len(entries),
                average_interval_days=round(sum(intervals) / len(intervals)),
            )
        )

    charges.sort(key=lambda item: (item.currency, item.name.casefold()))
    return RecurringChargesResponse(
        start_date=start_date,
        end_date=today,
        recurring_charges=charges,
    )
