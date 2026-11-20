import csv
import hashlib
import io
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.transaction_import import TransactionImport, TransactionImportError
from app.models.user import User
from app.services.categorization import categorize_with_rules, load_user_rules
from app.schemas.transaction_imports import (
    ImportDetail,
    ImportErrorResponse,
    ImportHistoryItem,
    ImportResponse,
)
from app.schemas.transactions import TransactionCreate

MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_ROWS = 5000
MAX_ERRORS_IN_UPLOAD_RESPONSE = 100
REQUIRED_COLUMNS = {"date", "description", "amount"}


def _fingerprint(
    transaction_date: date,
    description: str,
    amount: Decimal,
    currency: str,
    merchant: str | None,
) -> str:
    parts = (
        transaction_date.isoformat(),
        description.casefold(),
        format(amount, ".2f"),
        currency,
        (merchant or "").casefold(),
    )
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _raw_row(row: dict[Any, Any]) -> dict[str, Any]:
    return {
        str(key) if key is not None else "_extra_columns": value
        for key, value in row.items()
    }


def _duplicate_keys(
    db: Session,
    user_id: str,
    dates: Iterable[date],
) -> set[tuple[date, str, Decimal, str, str]]:
    duplicate_keys: set[tuple[date, str, Decimal, str, str]] = set()
    date_list = sorted(set(dates))
    for offset in range(0, len(date_list), 500):
        date_chunk = date_list[offset : offset + 500]
        statement = select(
            Transaction.transaction_date,
            Transaction.description,
            Transaction.amount,
            Transaction.currency,
            Transaction.merchant,
        ).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date.in_(date_chunk),
        )
        for transaction_date, description, amount, currency, merchant in db.execute(statement):
            duplicate_keys.add(
                (
                    transaction_date,
                    description.casefold(),
                    Decimal(amount),
                    currency,
                    (merchant or "").casefold(),
                )
            )
    return duplicate_keys


async def import_transactions_csv(
    db: Session,
    user: User,
    upload: UploadFile,
) -> ImportResponse:
    filename = (upload.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not filename or not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a .csv file")

    content = await upload.read(MAX_FILE_SIZE + 1)
    await upload.close()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="CSV exceeds the 5 MB limit")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV must use UTF-8 encoding") from error

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="CSV is empty or missing a header row")

    normalized_headers = [(header or "").strip().lower() for header in reader.fieldnames]
    if len(set(normalized_headers)) != len(normalized_headers):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="CSV contains duplicate column names")
    missing_columns = REQUIRED_COLUMNS - set(normalized_headers)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"CSV is missing required columns: {missing}",
        )
    reader.fieldnames = normalized_headers

    valid_rows: list[tuple[int, dict[str, Any], TransactionCreate, dict[str, Any]]] = []
    row_errors: list[tuple[int, str, dict[str, Any]]] = []
    rows_total = 0
    try:
        for row_number, row in enumerate(reader, start=2):
            rows_total += 1
            if rows_total > MAX_ROWS:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="CSV exceeds the 5,000-row limit")
            raw_data = _raw_row(row)
            if None in row:
                row_errors.append((row_number, "Row has more values than the header.", raw_data))
                continue
            if all(value is None or not value.strip() for value in row.values()):
                row_errors.append((row_number, "Row is empty.", raw_data))
                continue

            payload = {
                "transaction_date": row.get("date"),
                "description": row.get("description"),
                "amount": row.get("amount"),
                "merchant": row.get("merchant") or None,
                "currency": row.get("currency") or "USD",
                "category": row.get("category") or None,
            }
            try:
                validated = TransactionCreate.model_validate(payload)
            except ValidationError as error:
                messages = "; ".join(
                    f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                    for item in error.errors()
                )
                row_errors.append((row_number, messages[:500], raw_data))
                continue
            valid_rows.append((row_number, payload, validated, raw_data))
    except csv.Error as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV could not be parsed") from error

    seen = _duplicate_keys(db, user.id, (item[2].transaction_date for item in valid_rows))
    rules = load_user_rules(db, user.id)
    duplicate_count = 0
    transactions: list[Transaction] = []
    for _, _, validated, raw_data in valid_rows:
        duplicate_key = (
            validated.transaction_date,
            validated.description.casefold(),
            validated.amount,
            validated.currency,
            (validated.merchant or "").casefold(),
        )
        if duplicate_key in seen:
            duplicate_count += 1
            continue
        seen.add(duplicate_key)
        values = validated.model_dump()
        if values["category"] is None:
            values["category"], values["category_source"] = categorize_with_rules(
                values["description"],
                values["merchant"],
                rules,
            )
        else:
            values["category_source"] = "manual"
        transactions.append(Transaction(user_id=user.id, **values))

    import_record = TransactionImport(
        user_id=user.id,
        filename=filename[:255],
        rows_total=rows_total,
        imported_count=len(transactions),
        duplicate_count=duplicate_count,
        invalid_count=len(row_errors),
    )
    db.add(import_record)
    db.flush()
    db.add_all(transactions)
    db.add_all(
        TransactionImportError(
            import_id=import_record.id,
            row_number=row_number,
            message=message,
            raw_data=raw_data,
        )
        for row_number, message, raw_data in row_errors
    )
    db.commit()

    return ImportResponse(
        batch_id=import_record.id,
        filename=import_record.filename,
        rows_total=rows_total,
        imported_count=len(transactions),
        duplicate_count=duplicate_count,
        invalid_count=len(row_errors),
        errors=[
            ImportErrorResponse(row_number=row_number, message=message, raw_data=raw_data)
            for row_number, message, raw_data in row_errors[:MAX_ERRORS_IN_UPLOAD_RESPONSE]
        ],
    )


def list_imports(db: Session, user: User, limit: int, offset: int) -> list[TransactionImport]:
    statement = (
        select(TransactionImport)
        .where(TransactionImport.user_id == user.id)
        .order_by(TransactionImport.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


def read_import(
    db: Session,
    user: User,
    import_id: str,
    error_limit: int,
    error_offset: int,
) -> ImportDetail:
    batch = db.scalar(
        select(TransactionImport).where(
            TransactionImport.id == import_id,
            TransactionImport.user_id == user.id,
        )
    )
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    errors = db.scalars(
        select(TransactionImportError)
        .where(TransactionImportError.import_id == batch.id)
        .order_by(TransactionImportError.row_number)
        .offset(error_offset)
        .limit(error_limit)
    )
    return ImportDetail(
        **ImportHistoryItem.model_validate(batch).model_dump(),
        errors=[ImportErrorResponse.model_validate(error) for error in errors],
    )
