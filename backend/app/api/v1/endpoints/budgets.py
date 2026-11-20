from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models.budget import Budget
from app.models.user import User
from app.schemas.budgets import BudgetCreate, BudgetProgress, BudgetUpdate
from app.services.budgets import budget_progress, list_budgets

router = APIRouter()


@router.post("", response_model=BudgetProgress, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetProgress:
    values = payload.model_dump()
    existing = db.scalar(
        select(Budget).where(
            Budget.user_id == user.id,
            Budget.category == values["category"],
            Budget.currency == values["currency"],
            Budget.month == values["month"],
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A budget already exists for this category and month")

    budget = Budget(user_id=user.id, **values)
    db.add(budget)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A budget already exists for this category and month",
        )
    db.refresh(budget)
    return budget_progress(db, user, [budget])[0]


@router.get("", response_model=list[BudgetProgress])
def get_budgets(
    month: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BudgetProgress]:
    selected_month = month or date.today().replace(day=1)
    if selected_month.day != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="month must be the first day of the month",
        )
    return list_budgets(db, user, selected_month)


@router.put("/{budget_id}", response_model=BudgetProgress)
def update_budget(
    budget_id: str,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetProgress:
    budget = db.scalar(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user.id)
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    budget.amount = payload.amount
    db.commit()
    db.refresh(budget)
    return budget_progress(db, user, [budget])[0]
