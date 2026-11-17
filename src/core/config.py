from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]

DEFAULT_SECRET_KEY = "change-me-in-production"
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = BASE_DIR / "blog_engine.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH}"

MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    ENVIRONMENT: Environment = "development"
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SESSION_COOKIE_SECURE: bool = False
    DEBUG: bool = False
    APP_NAME: str = "FastAPI Blog"
    APP_VERSION: str = "1.0.0"
    BLOG_DATABASE_URL: str = DEFAULT_DATABASE_URL
    BLOG_SEED_DEMO: bool = True
    BLOG_ADMIN_USERNAME: str = ""
    BLOG_ADMIN_PASSWORD: str = ""
    API_RATE_LIMIT_PER_MINUTE: int = 120
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8000"]


class ProductionConfigError(RuntimeError):
    """Raised at startup when production settings are unsafe."""


def validate_production_settings(config: Settings) -> None:
    if config.ENVIRONMENT != "production":
        return

    problems: list[str] = []

    if config.SECRET_KEY == DEFAULT_SECRET_KEY:
        problems.append(
            "SECRET_KEY is the insecure default; generate a strong secret (e.g. `openssl rand -hex 32`)"
        )
    elif len(config.SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
        problems.append(
            f"SECRET_KEY is too short; use at least {MIN_SECRET_KEY_LENGTH} characters"
        )
    if config.DEBUG:
        problems.append("DEBUG must be disabled in production")
    if not config.SESSION_COOKIE_SECURE:
        problems.append("SESSION_COOKIE_SECURE must be true when serving over HTTPS")
    if config.BLOG_SEED_DEMO:
        problems.append(
            "BLOG_SEED_DEMO must be disabled in production; demo accounts ship well-known passwords"
        )

    if problems:
        raise ProductionConfigError(
            "Refusing to start with insecure production settings: " + "; ".join(problems)
        )


settings = Settings()
