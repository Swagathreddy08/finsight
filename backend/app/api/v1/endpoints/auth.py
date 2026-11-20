import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db import get_db, set_rls_user
from app.models.auth_session import AuthSession, RefreshToken
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)

router = APIRouter()
refresh_cookie_path = f"{settings.api_v1_prefix}/auth"


def _find_user_by_email(db: Session, email: str) -> User | None:
    if db.get_bind().dialect.name != "postgresql":
        return db.scalar(select(User).where(User.email == email))

    row = db.execute(
        text("SELECT * FROM public.finsight_auth_user_by_email(:email)"),
        {"email": email},
    ).mappings().one_or_none()
    return User(**row) if row is not None else None


def _create_session(db: Session, user: User) -> tuple[AuthResponse, str]:
    now = datetime.now(timezone.utc)
    set_rls_user(db, user.id)
    session = AuthSession(
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    refresh_token = secrets.token_urlsafe(48)
    db.add(session)
    db.flush()
    refresh_token = f"{user.id}.{session.id}.{refresh_token}"
    db.add(
        RefreshToken(
            session_id=session.id,
            token_hash=hash_refresh_token(refresh_token),
            created_at=now,
            expires_at=session.expires_at,
        )
    )
    db.commit()
    return AuthResponse(access_token=create_access_token(user.id, session.id), user=user), refresh_token


def _invalid_refresh_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token is invalid or expired",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path=refresh_cookie_path,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path=refresh_cookie_path,
    )


def _validate_auth_origin(request: Request) -> None:
    if settings.app_env.lower() == "production":
        origin = request.headers.get("origin")
        if origin != settings.frontend_url.rstrip("/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication requests must come from the configured application origin",
            )


def _refresh_identity(token: str) -> tuple[str, str] | None:
    try:
        user_id, session_id, secret = token.split(".", 2)
        uuid.UUID(user_id)
        uuid.UUID(session_id)
    except (ValueError, AttributeError):
        return None
    if len(secret) < 32:
        return None
    return user_id, session_id


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    _validate_auth_origin(request)
    email = str(payload.email).strip().lower()
    existing = _find_user_by_email(db, email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    set_rls_user(db, user.id)
    db.add(user)
    db.flush()
    auth_response, refresh_token = _create_session(db, user)
    _set_refresh_cookie(response, refresh_token)
    return auth_response


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    _validate_auth_origin(request)
    email = str(payload.email).strip().lower()
    user = _find_user_by_email(db, email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    auth_response, refresh_token = _create_session(db, user)
    _set_refresh_cookie(response, refresh_token)
    return auth_response


@router.post("/refresh", response_model=AuthResponse)
def refresh_tokens(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_cookie_name),
    db: Session = Depends(get_db),
) -> AuthResponse:
    _validate_auth_origin(request)
    if refresh_token is None:
        raise _invalid_refresh_token()

    identity = _refresh_identity(refresh_token)
    if identity is None:
        raise _invalid_refresh_token()
    user_id, session_id = identity
    set_rls_user(db, user_id)
    now = datetime.now(timezone.utc)
    refresh_token = db.scalar(
        select(RefreshToken)
        .where(
            RefreshToken.session_id == session_id,
            RefreshToken.token_hash == hash_refresh_token(refresh_token),
        )
        .with_for_update()
    )
    if refresh_token is None:
        raise _invalid_refresh_token()

    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.id == session_id, AuthSession.user_id == user_id)
        .with_for_update()
    )
    if session is None:
        raise _invalid_refresh_token()

    if refresh_token.consumed_at is not None:
        if session.revoked_at is None:
            session.revoked_at = now
            db.commit()
        raise _invalid_refresh_token()

    if (
        session.revoked_at is not None
        or _as_utc(session.expires_at) <= now
    ):
        raise _invalid_refresh_token()

    user = db.scalar(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    if user is None:
        session.revoked_at = now
        db.commit()
        raise _invalid_refresh_token()

    refresh_token.consumed_at = now
    next_refresh_token = f"{user_id}.{session.id}.{secrets.token_urlsafe(48)}"
    db.add(
        RefreshToken(
            session_id=session.id,
            token_hash=hash_refresh_token(next_refresh_token),
            created_at=now,
            expires_at=session.expires_at,
        )
    )
    db.commit()
    _set_refresh_cookie(response, next_refresh_token)
    return AuthResponse(access_token=create_access_token(user.id, session.id), user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_cookie_name),
    db: Session = Depends(get_db),
) -> None:
    _validate_auth_origin(request)
    identity = _refresh_identity(refresh_token) if refresh_token else None
    if identity is not None:
        user_id, session_id = identity
        set_rls_user(db, user_id)
        refresh_record = db.scalar(
            select(RefreshToken).where(
                RefreshToken.session_id == session_id,
                RefreshToken.token_hash == hash_refresh_token(refresh_token),
            )
        )
        session = db.scalar(
            select(AuthSession).where(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
            )
        )
        if refresh_record is not None and session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserResponse)
def read_current_user(user: User = Depends(get_current_user)) -> User:
    return user
