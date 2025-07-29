from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import aiomysql

from core.security import get_current_user
from database.connection import get_database
from pathlib import Path

router = APIRouter()

# Templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

@router.get("/", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: aiomysql.Connection = Depends(get_database)
):
    """Display user dashboard with their articles"""
    try:
        cursor = await db.cursor()
        await cursor.execute(
            "SELECT * FROM articles WHERE author = %s ORDER BY created_at DESC",
            (current_user["username"],)
        )
        articles = await cursor.fetchall()
        await cursor.close()
        
        return templates.TemplateResponse(
            "dashboard.html", 
            {
                "request": request, 
                "articles": articles,
                "msg": "No Articles Found" if not articles else None
            }
        )
    except Exception:
        return templates.TemplateResponse(
            "dashboard.html", 
            {
                "request": request, 
                "articles": [],
                "current_user": current_user,
                "msg": "No Articles Found"
            }
        )

@router.get("/add_article", response_class=HTMLResponse)
async def add_article_page(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Display add article page"""
    return templates.TemplateResponse(
        "add_article.html", 
        {"request": request, "current_user": current_user}
    )

@router.get("/edit_article/{article_id}", response_class=HTMLResponse)
async def edit_article_page(
    article_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: aiomysql.Connection = Depends(get_database)
):
    """Display edit article page"""
    try:
        cursor = await db.cursor()
        await cursor.execute(
            "SELECT * FROM articles WHERE id = %s AND author = %s",
            (article_id, current_user["username"])
        )
        article = await cursor.fetchone()
        await cursor.close()
        
        if not article:
            return RedirectResponse(url="/dashboard", status_code=302)
        
        return templates.TemplateResponse(
            "edit_article.html", 
            {
                "request": request, 
                "article": article,
                "current_user": current_user
            }
        )
    except Exception:
        return RedirectResponse(url="/dashboard", status_code=302)
