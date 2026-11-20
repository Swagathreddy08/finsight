from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CategorySpending(BaseModel):
    category: str
    amount: Decimal


class CurrencySummary(BaseModel):
    currency: str
    income: Decimal
    expenses: Decimal
    net: Decimal
    transaction_count: int
    spending_by_category: list[CategorySpending]


class AnalyticsSummary(BaseModel):
    start_date: date
    end_date: date
    currency_summaries: list[CurrencySummary]
