from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import timedelta
import aiomysql

from core.schemas import UserCreate, UserLogin, Token
from core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    authenticate_user,
    get_user_by_username
)
from core.config import settings
from database.connection import get_database
from pathlib import Path

router = APIRouter()

# Templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

@router.post("/login")
async def login_for_access_token(
    username: str = Form(...),
    password: str = Form(...),
    db: aiomysql.Connection = Depends(get_database)
):
    """Authenticate user and return access token"""
    user = await authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html", 
            {"request": {}, "error": "Incorrect username or password"},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    # Create response with redirect to dashboard
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return response

@router.post("/register")
async def register_user(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: aiomysql.Connection = Depends(get_database)
):
    """Register a new user"""
    # Validate passwords match
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Passwords do not match"}
        )
    
    # Check if user already exists
    existing_user = await get_user_by_username(db, username)
    if existing_user:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Username already registered"}
        )
    
    # Hash password and create user
    hashed_password = get_password_hash(password)
    
    try:
        cursor = await db.cursor()
        await cursor.execute(
            "INSERT INTO users (name, email, username, password) VALUES (%s, %s, %s, %s)",
            (name, email, username, hashed_password)
        )
        await db.commit()
        await cursor.close()
        
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        await db.rollback()
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Registration failed"}
        )

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Display registration page"""
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/logout")
async def logout():
    """Logout user"""
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response
