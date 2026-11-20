"""create transaction import history and row errors

Revision ID: 20261119_0003
Revises: 20261119_0002
Create Date: 2026-11-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261119_0003"
down_revision: Union[str, Sequence[str], None] = "20261119_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transaction_imports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("rows_total", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("invalid_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transaction_imports_user_id", "transaction_imports", ["user_id"])
    op.create_table(
        "transaction_import_errors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("import_id", sa.String(length=36), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["import_id"], ["transaction_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transaction_import_errors_import_id",
        "transaction_import_errors",
        ["import_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_import_errors_import_id", table_name="transaction_import_errors")
    op.drop_table("transaction_import_errors")
    op.drop_index("ix_transaction_imports_user_id", table_name="transaction_imports")
    op.drop_table("transaction_imports")
