"""add user categorization rules and transaction category source

Revision ID: 20261119_0005
Revises: 20261119_0004
Create Date: 2026-11-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261119_0005"
down_revision: Union[str, Sequence[str], None] = "20261119_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("category_source", sa.String(length=20), nullable=True))
    op.create_table(
        "categorization_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("keyword", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("match_field", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "keyword",
            "match_field",
            name="uq_categorization_rules_user_keyword_field",
        ),
    )
    op.create_index("ix_categorization_rules_user_id", "categorization_rules", ["user_id"])
    op.create_index(
        "ix_categorization_rules_user_priority",
        "categorization_rules",
        ["user_id", "priority"],
    )


def downgrade() -> None:
    op.drop_index("ix_categorization_rules_user_priority", table_name="categorization_rules")
    op.drop_index("ix_categorization_rules_user_id", table_name="categorization_rules")
    op.drop_table("categorization_rules")
    op.drop_column("transactions", "category_source")
