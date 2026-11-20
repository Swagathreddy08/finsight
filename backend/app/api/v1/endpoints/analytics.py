from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsSummary
from app.schemas.recurring import RecurringChargesResponse
from app.services.analytics import spending_summary
from app.services.recurring import find_recurring_charges

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
def get_spending_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalyticsSummary:
    return spending_summary(db, user, start_date, end_date)


@router.get("/recurring", response_model=RecurringChargesResponse)
def get_recurring_charges(
    months: int = Query(default=6, ge=3, le=12),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecurringChargesResponse:
    return find_recurring_charges(db, user, months)
