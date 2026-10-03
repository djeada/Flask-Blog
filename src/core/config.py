from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    DEBUG: bool = False
    APP_NAME: str = "FastAPI Blog"
    APP_VERSION: str = "1.0.0"
    BLOG_DATABASE_URL: str = "sqlite:///./blog_engine.db"
    BLOG_SEED_DEMO: bool = True
    API_RATE_LIMIT_PER_MINUTE: int = 120
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8000"]


settings = Settings()
