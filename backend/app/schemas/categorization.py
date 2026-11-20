from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategorizationRuleCreate(BaseModel):
    keyword: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=80)
    match_field: Literal["any", "merchant", "description"] = "any"
    priority: int = Field(default=0, ge=0, le=100)

    @field_validator("keyword", "category")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value


class CategorizationRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    keyword: str
    category: str
    match_field: Literal["any", "merchant", "description"]
    priority: int
    created_at: datetime


class TransactionCategoryUpdate(BaseModel):
    category: str | None

    @field_validator("category")
    @classmethod
    def trim_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Category cannot be blank")
        return value
