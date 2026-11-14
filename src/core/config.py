from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change-me-in-production"
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = BASE_DIR / "blog_engine.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SESSION_COOKIE_SECURE: bool = False
    DEBUG: bool = False
    APP_NAME: str = "FastAPI Blog"
    APP_VERSION: str = "1.0.0"
    BLOG_DATABASE_URL: str = DEFAULT_DATABASE_URL
    BLOG_SEED_DEMO: bool = True
    API_RATE_LIMIT_PER_MINUTE: int = 120
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8000"]


settings = Settings()
