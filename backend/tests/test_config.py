import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _production_settings(**overrides: str) -> dict[str, str]:
    values = {
        "app_env": "production",
        "database_url": "postgresql+psycopg://user:password@localhost/finsight",
        "frontend_url": "https://finsight.example",
        "jwt_secret_key": "s" * 64,
        "secure_cookies": "true",
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    "overrides",
    [
        {"jwt_secret_key": "replace-with-a-long-random-secret"},
        {"secure_cookies": "false"},
        {"frontend_url": "https://finsight.example/app"},
        {"database_url": "sqlite:///local.db"},
    ],
)
def test_production_settings_reject_unsafe_configuration(
    overrides: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        Settings(**_production_settings(**overrides))


def test_production_settings_accept_secure_origin_and_postgres() -> None:
    settings = Settings(**_production_settings())

    assert settings.app_env == "production"
    assert settings.secure_cookies is True
