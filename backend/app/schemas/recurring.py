from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class RecurringCharge(BaseModel):
    name: str
    currency: str
    typical_amount: Decimal
    category: str | None
    last_seen: date
    occurrences: int
    average_interval_days: int


class RecurringChargesResponse(BaseModel):
    start_date: date
    end_date: date
    recurring_charges: list[RecurringCharge]
