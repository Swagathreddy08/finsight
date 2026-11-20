from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from urllib.parse import urlparse


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    database_url: str = (
        "postgresql+psycopg://finsight:replace-me@localhost:5432/finsight"
    )
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "replace-with-a-long-random-secret"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    secure_cookies: bool = False
    refresh_cookie_name: str = "finsight_refresh"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env.lower() != "production":
            return self

        if len(self.jwt_secret_key) < 64 or self.jwt_secret_key.startswith("replace-"):
            raise ValueError("Production requires a JWT_SECRET_KEY with at least 64 characters")
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("Production requires PostgreSQL")
        if not self.secure_cookies:
            raise ValueError("Production requires SECURE_COOKIES=true")

        frontend = urlparse(self.frontend_url)
        if frontend.scheme != "https" or not frontend.netloc:
            raise ValueError("Production FRONTEND_URL must be an HTTPS origin")
        if frontend.path or frontend.query or frontend.fragment:
            raise ValueError("FRONTEND_URL must be an origin without a path or query")
        return self


settings = Settings()
