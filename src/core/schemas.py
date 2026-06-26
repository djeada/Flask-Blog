from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    confirm_password: str
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @field_validator('username')
    @classmethod
    def username_length(cls, v):
        if len(v) < 4 or len(v) > 25:
            raise ValueError('Username must be between 4 and 25 characters')
        return v
    
    @field_validator('name')
    @classmethod
    def name_length(cls, v):
        if len(v) < 1 or len(v) > 50:
            raise ValueError('Name must be between 1 and 50 characters')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class ArticleBase(BaseModel):
    title: str
    body: str
    
    @field_validator('title')
    @classmethod
    def title_length(cls, v):
        if len(v) < 1 or len(v) > 200:
            raise ValueError('Title must be between 1 and 200 characters')
        return v
    
    @field_validator('body')
    @classmethod
    def body_length(cls, v):
        if len(v) < 30:
            raise ValueError('Body must be at least 30 characters')
        return v

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(ArticleBase):
    pass

class ArticleResponse(ArticleBase):
    id: int
    author: str
    created_at: Optional[datetime] = None
    image: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
