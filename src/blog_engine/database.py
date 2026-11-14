from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.BLOG_DATABASE_URL,
    connect_args={"check_same_thread": False}
    if settings.BLOG_DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_blog_tables() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_user_password_column()


def _ensure_user_password_column() -> None:
    inspector = inspect(engine)
    if "blog_users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("blog_users")}
    if "password_hash" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE blog_users ADD COLUMN password_hash VARCHAR(255)")
            )


def get_blog_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
