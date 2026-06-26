from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "secret_pass"
    DB_NAME: str = "blog_db"
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-here-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application settings
    DEBUG: bool = True
    APP_NAME: str = "FastAPI Blog"
    APP_VERSION: str = "1.1.0"
    ENABLE_LEGACY_MYSQL: bool = False
    BLOG_DATABASE_URL: str = "sqlite:///./blog_engine.db"
    BLOG_SEED_DEMO: bool = True
    API_RATE_LIMIT_PER_MINUTE: int = 120
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    @property
    def database_url(self) -> str:
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
settings = Settings()
