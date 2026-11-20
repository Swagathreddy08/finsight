"""enable row-level security for account-owned data

Revision ID: 20261120_0007
Revises: 20261119_0006
Create Date: 2026-11-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261120_0007"
down_revision: Union[str, Sequence[str], None] = "20261119_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_USER_TABLES = (
    "transactions",
    "budgets",
    "categorization_rules",
    "auth_sessions",
    "transaction_imports",
)
_APP_TABLES = (
    "users",
    *_USER_TABLES,
    "refresh_tokens",
    "transaction_import_errors",
)


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.finsight_auth_user_by_email(input_email TEXT)
        RETURNS TABLE (
            id VARCHAR,
            email VARCHAR,
            full_name VARCHAR,
            password_hash VARCHAR,
            is_active BOOLEAN,
            created_at TIMESTAMPTZ
        )
        LANGUAGE SQL
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT u.id, u.email, u.full_name, u.password_hash, u.is_active, u.created_at
            FROM public.users AS u
            WHERE lower(u.email) = lower(input_email)
        $function$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION public.finsight_auth_user_by_email(TEXT) FROM PUBLIC")
    op.execute(
        """
        DO $block$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'finsight_app') THEN
                EXECUTE 'GRANT USAGE ON SCHEMA public TO finsight_app';
                EXECUTE 'GRANT EXECUTE ON FUNCTION public.finsight_auth_user_by_email(TEXT) TO finsight_app';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO finsight_app';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO finsight_app';
            END IF;
        END
        $block$
        """
    )
    for table in _APP_TABLES:
        op.execute(
            f"""
            DO $block$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'finsight_app') THEN
                    EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{table} TO finsight_app';
                END IF;
            END
            $block$
            """
        )

    for table in _USER_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY user_isolation ON public.{table}
            USING (user_id = current_setting('app.user_id', true))
            WITH CHECK (user_id = current_setting('app.user_id', true))
            """
        )

    op.execute("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.users FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY user_isolation ON public.users
        USING (id = current_setting('app.user_id', true))
        WITH CHECK (id = current_setting('app.user_id', true))
        """
    )
    op.execute("ALTER TABLE public.refresh_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.refresh_tokens FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY user_isolation ON public.refresh_tokens
        USING (
            EXISTS (
                SELECT 1
                FROM public.auth_sessions AS s
                WHERE s.id = refresh_tokens.session_id
                  AND s.user_id = current_setting('app.user_id', true)
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.auth_sessions AS s
                WHERE s.id = refresh_tokens.session_id
                  AND s.user_id = current_setting('app.user_id', true)
            )
        )
        """
    )
    op.execute("ALTER TABLE public.transaction_import_errors ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.transaction_import_errors FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY user_isolation ON public.transaction_import_errors
        USING (
            EXISTS (
                SELECT 1
                FROM public.transaction_imports AS i
                WHERE i.id = transaction_import_errors.import_id
                  AND i.user_id = current_setting('app.user_id', true)
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.transaction_imports AS i
                WHERE i.id = transaction_import_errors.import_id
                  AND i.user_id = current_setting('app.user_id', true)
            )
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $block$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'finsight_app') THEN
                EXECUTE 'REVOKE EXECUTE ON FUNCTION public.finsight_auth_user_by_email(TEXT) FROM finsight_app';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM finsight_app';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM finsight_app';
            END IF;
        END
        $block$
        """
    )
    for table in _APP_TABLES:
        op.execute(
            f"""
            DO $block$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'finsight_app') THEN
                    EXECUTE 'REVOKE ALL ON TABLE public.{table} FROM finsight_app';
                END IF;
            END
            $block$
            """
        )
    for table in (
        "transaction_import_errors",
        "refresh_tokens",
        "users",
        *_USER_TABLES,
    ):
        op.execute(f"DROP POLICY IF EXISTS user_isolation ON public.{table}")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY")

    op.execute("DROP FUNCTION IF EXISTS public.finsight_auth_user_by_email(TEXT)")
