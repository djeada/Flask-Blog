from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blog_engine.database import Base


class Role(str, Enum):
    ADMIN = "Admin"
    EDITOR = "Editor"
    AUTHOR = "Author"
    CONTRIBUTOR = "Contributor"
    SUBSCRIBER = "Subscriber"


class PostStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class BlogUser(Base):
    __tablename__ = "blog_users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    role: Mapped[Role] = mapped_column(SqlEnum(Role), nullable=False, default=Role.SUBSCRIBER)

    posts: Mapped[list["Post"]] = relationship(back_populates="author")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PostStatus] = mapped_column(
        SqlEnum(PostStatus), nullable=False, default=PostStatus.DRAFT
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("blog_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    author: Mapped[BlogUser] = relationship(back_populates="posts")
