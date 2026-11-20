from datetime import date, datetime
from decimal import Decimal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionCreate(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    merchant: str | None = Field(default=None, max_length=200)
    amount: Decimal = Field(gt=Decimal("-1000000000000"), lt=Decimal("1000000000000"))
    currency: str = Field(default="USD", min_length=3, max_length=3)
    category: str | None = Field(default=None, max_length=80)
    transaction_date: date

    @field_validator("description", "merchant", "category")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value

    @field_validator("amount")
    @classmethod
    def require_cents_precision(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("Amount cannot be zero")
        if value.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than two decimal places")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.upper()
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError("Currency must be a three-letter code")
        return value


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str
    merchant: str | None
    amount: Decimal
    currency: str
    category: str | None
    category_source: str | None
    transaction_date: date
    created_at: datetime
