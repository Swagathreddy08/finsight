from datetime import date
from decimal import Decimal
import re

from pydantic import BaseModel, Field, field_validator, model_validator


class BudgetCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    amount: Decimal = Field(gt=0, lt=Decimal("1000000000000"))
    month: date = Field(default_factory=lambda: date.today().replace(day=1))

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Category cannot be blank")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.upper()
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError("Currency must be a three-letter code")
        return value

    @field_validator("amount")
    @classmethod
    def require_cents_precision(cls, value: Decimal) -> Decimal:
        if value.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than two decimal places")
        return value

    @field_validator("month")
    @classmethod
    def require_first_day_of_month(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("Month must be the first day of the month")
        return value


class BudgetUpdate(BaseModel):
    amount: Decimal = Field(gt=0, lt=Decimal("1000000000000"))

    @field_validator("amount")
    @classmethod
    def require_cents_precision(cls, value: Decimal) -> Decimal:
        if value.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than two decimal places")
        return value


class BudgetProgress(BaseModel):
    id: str
    category: str
    currency: str
    month: date
    budget_amount: Decimal
    spent: Decimal
    remaining: Decimal
    percent_used: Decimal
