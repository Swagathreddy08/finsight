from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ImportErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_number: int
    message: str
    raw_data: dict[str, Any]


class ImportResponse(BaseModel):
    batch_id: str
    filename: str
    rows_total: int
    imported_count: int
    duplicate_count: int
    invalid_count: int
    errors: list[ImportErrorResponse]


class ImportHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    rows_total: int
    imported_count: int
    duplicate_count: int
    invalid_count: int
    created_at: datetime


class ImportDetail(ImportHistoryItem):
    errors: list[ImportErrorResponse]
