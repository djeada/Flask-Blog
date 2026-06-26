from collections.abc import Generator

from sqlalchemy import create_engine
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


def get_blog_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
