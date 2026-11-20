from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@event.listens_for(Session, "after_begin")
def _apply_rls_user_context(
    session: Session,
    _transaction: object,
    connection: Connection,
) -> None:
    user_id = session.info.get("user_id")
    if user_id and connection.dialect.name == "postgresql":
        connection.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": user_id},
        )


def set_rls_user(session: Session, user_id: str) -> None:
    session.info["user_id"] = user_id
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {"user_id": user_id},
        )


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
