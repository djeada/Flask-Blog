from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import os
from pathlib import Path

from database.connection import get_database, init_db_pool, close_db_pool, create_tables
from routers import auth, articles, dashboard, pages
from core.config import settings
from core.security import get_current_user_optional

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="A modern blog application built with FastAPI"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Templates
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database connection pool and create tables"""
    await init_db_pool()
    await create_tables()
    print("🚀 FastAPI Blog application started successfully!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection pool"""
    await close_db_pool()
    print("👋 FastAPI Blog application shut down gracefully!")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(pages.router, tags=["pages"])

@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request, 
    db=Depends(get_database),
    current_user=Depends(get_current_user_optional)
):
    """Home page showing all articles"""
    try:
        cursor = await db.cursor()
        await cursor.execute("SELECT * FROM articles ORDER BY created_at DESC")
        articles = await cursor.fetchall()
        await cursor.close()
    except Exception as e:
        articles = []
    
    return templates.TemplateResponse(
        "home.html", 
        {
            "request": request, 
            "articles": articles,
            "current_user": current_user
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
