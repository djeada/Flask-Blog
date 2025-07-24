from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List
import aiomysql

from core.schemas import ArticleCreate, ArticleUpdate, ArticleResponse
from core.security import get_current_user
from database.connection import get_database
from pathlib import Path

router = APIRouter()

# Templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

@router.get("/", response_class=HTMLResponse)
async def articles_page(
    request: Request,
    db: aiomysql.Connection = Depends(get_database)
):
    """Display all articles page"""
    try:
        cursor = await db.cursor()
        await cursor.execute("SELECT * FROM articles ORDER BY created_at DESC")
        articles = await cursor.fetchall()
        await cursor.close()
    except Exception:
        articles = []
    
    return templates.TemplateResponse(
        "articles.html", 
        {"request": request, "articles": articles}
    )

@router.get("/{article_id}", response_class=HTMLResponse)
async def single_article_page(
    article_id: int,
    request: Request,
    db: aiomysql.Connection = Depends(get_database)
):
    """Display single article page"""
    try:
        cursor = await db.cursor()
        await cursor.execute("SELECT * FROM articles WHERE id = %s", (article_id,))
        article = await cursor.fetchone()
        await cursor.close()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return templates.TemplateResponse(
            "article.html", 
            {"request": request, "article": article}
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Article not found")

@router.post("/")
async def create_article(
    title: str = Form(...),
    body: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: aiomysql.Connection = Depends(get_database)
):
    """Create a new article"""
    # Validate input
    if len(title) < 1 or len(title) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title must be between 1 and 200 characters"
        )
    
    if len(body) < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Body must be at least 30 characters"
        )
    
    try:
        cursor = await db.cursor()
        await cursor.execute(
            "INSERT INTO articles (title, body, author) VALUES (%s, %s, %s)",
            (title, body, current_user["username"])
        )
        await db.commit()
        await cursor.close()
        
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create article"
        )

@router.put("/{article_id}")
async def update_article(
    article_id: int,
    title: str = Form(...),
    body: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: aiomysql.Connection = Depends(get_database)
):
    """Update an existing article"""
    # Validate input
    if len(title) < 1 or len(title) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title must be between 1 and 200 characters"
        )
    
    if len(body) < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Body must be at least 30 characters"
        )
    
    try:
        cursor = await db.cursor()
        
        # Check if article exists and belongs to user
        await cursor.execute(
            "SELECT * FROM articles WHERE id = %s AND author = %s",
            (article_id, current_user["username"])
        )
        article = await cursor.fetchone()
        
        if not article:
            await cursor.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found or you don't have permission to edit it"
            )
        
        # Update article
        await cursor.execute(
            "UPDATE articles SET title = %s, body = %s WHERE id = %s",
            (title, body, article_id)
        )
        await db.commit()
        await cursor.close()
        
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update article"
        )

@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiomysql.Connection = Depends(get_database)
):
    """Delete an article"""
    try:
        cursor = await db.cursor()
        
        # Check if article exists and belongs to user
        await cursor.execute(
            "SELECT * FROM articles WHERE id = %s AND author = %s",
            (article_id, current_user["username"])
        )
        article = await cursor.fetchone()
        
        if not article:
            await cursor.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found or you don't have permission to delete it"
            )
        
        # Delete article
        await cursor.execute("DELETE FROM articles WHERE id = %s", (article_id,))
        await db.commit()
        await cursor.close()
        
        return {"message": "Article deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete article"
        )
