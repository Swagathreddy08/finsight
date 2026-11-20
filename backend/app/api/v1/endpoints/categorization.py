from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models.categorization_rule import CategorizationRule
from app.models.user import User
from app.schemas.categorization import CategorizationRuleCreate, CategorizationRuleResponse

router = APIRouter()


@router.get("/rules", response_model=list[CategorizationRuleResponse])
def list_rules(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CategorizationRule]:
    statement = (
        select(CategorizationRule)
        .where(CategorizationRule.user_id == user.id)
        .order_by(CategorizationRule.priority.desc(), CategorizationRule.created_at)
    )
    return list(db.scalars(statement))


@router.post(
    "/rules",
    response_model=CategorizationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rule(
    payload: CategorizationRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CategorizationRule:
    duplicate = db.scalar(
        select(CategorizationRule).where(
            CategorizationRule.user_id == user.id,
            func.lower(CategorizationRule.keyword) == payload.keyword.lower(),
            CategorizationRule.match_field == payload.match_field,
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This rule already exists")

    rule = CategorizationRule(user_id=user.id, **payload.model_dump())
    db.add(rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This rule already exists")
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    rule = db.scalar(
        select(CategorizationRule).where(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == user.id,
        )
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    db.delete(rule)
    db.commit()
