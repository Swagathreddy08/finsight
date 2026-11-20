from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models.transaction import Transaction
from app.models.transaction_import import TransactionImport
from app.models.user import User
from app.schemas.categorization import TransactionCategoryUpdate
from app.services.categorization import categorize_with_rules, load_user_rules
from app.schemas.transaction_imports import ImportDetail, ImportHistoryItem, ImportResponse
from app.schemas.transactions import TransactionCreate, TransactionResponse
from app.services.transaction_imports import import_transactions_csv, list_imports, read_import

router = APIRouter()


@router.post("/import", response_model=ImportResponse, status_code=status.HTTP_201_CREATED)
async def upload_transactions_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImportResponse:
    return await import_transactions_csv(db, user, file)


@router.get("/imports", response_model=list[ImportHistoryItem])
def get_transaction_imports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TransactionImport]:
    return list_imports(db, user, limit, offset)


@router.get("/imports/{import_id}", response_model=ImportDetail)
def get_transaction_import(
    import_id: str,
    error_limit: int = Query(default=100, ge=1, le=500),
    error_offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImportDetail:
    return read_import(db, user, import_id, error_limit, error_offset)


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Transaction:
    values = payload.model_dump()
    if values["category"] is None:
        rules = load_user_rules(db, user.id)
        values["category"], values["category_source"] = categorize_with_rules(
            values["description"],
            values["merchant"],
            rules,
        )
    else:
        values["category_source"] = "manual"
    transaction = Transaction(user_id=user.id, **values)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Transaction]:
    statement = (
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


@router.patch("/{transaction_id}/category", response_model=TransactionResponse)
def update_transaction_category(
    transaction_id: str,
    payload: TransactionCategoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Transaction:
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user.id,
        )
    )
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    transaction.category = payload.category
    transaction.category_source = "manual" if payload.category else None
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/{transaction_id}", response_model=TransactionResponse)
def read_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Transaction:
    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user.id,
    )
    transaction = db.scalar(statement)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction
