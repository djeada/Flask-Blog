from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from blog_engine.models import PostStatus, Role


class Principal(BaseModel):
    user_id: int
    username: str
    role: Role


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"detail": "Post not found"}]}
    )


class PostBase(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
        examples=["Shipping the first API version"],
    )
    body: str = Field(
        min_length=1,
        description="Markdown body.",
        examples=["# Release notes\n\nThe v1 API is now available."],
    )
    status: PostStatus = Field(default=PostStatus.DRAFT, examples=["published"])

    @field_validator("title", "body")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be blank")
        return value


class PostCreate(PostBase):
    author_id: int | None = Field(
        default=None,
        description="Optional for Admin/Editor. Other roles always create as themselves.",
        examples=[1],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "API launch",
                    "body": "Published through the REST API.",
                    "status": "published",
                    "author_id": 1,
                }
            ]
        }
    )


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1, description="Markdown body.")
    status: PostStatus | None = None
    author_id: int | None = None

    @field_validator("title", "body")
    @classmethod
    def optional_non_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Field cannot be blank")
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Updated API launch",
                    "body": "Updated Markdown body.",
                    "status": "published",
                }
            ]
        }
    )


class PostResponse(PostBase):
    id: int
    author_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenClaims(BaseModel):
    sub: str
    user_id: int
    role: Role
