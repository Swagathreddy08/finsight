import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CategorizationRule(Base):
    __tablename__ = "categorization_rules"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "keyword",
            "match_field",
            name="uq_categorization_rules_user_keyword_field",
        ),
        Index("ix_categorization_rules_user_priority", "user_id", "priority"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    match_field: Mapped[Literal["any", "merchant", "description"]] = mapped_column(String(20), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
