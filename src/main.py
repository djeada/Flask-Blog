from collections import defaultdict, deque
from contextlib import asynccontextmanager
from time import time

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path

from database.connection import get_database, init_db_pool, close_db_pool, create_tables
from routers import api_v1_posts, auth, articles, dashboard, pages
from blog_engine.database import SessionLocal, create_blog_tables
from blog_engine.demo import seed_demo_content
from core.config import settings
from core.security import get_current_user_optional

rate_limit_buckets = defaultdict(deque)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_blog_tables()
    if settings.BLOG_SEED_DEMO:
        with SessionLocal() as db:
            seed_demo_content(db)
    if settings.ENABLE_LEGACY_MYSQL:
        await init_db_pool()
        await create_tables()
    print("FastAPI Blog application started successfully.")
    try:
        yield
    finally:
        if settings.ENABLE_LEGACY_MYSQL:
            await close_db_pool()
        print("FastAPI Blog application shut down gracefully.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="A modern blog application built with FastAPI",
    lifespan=lifespan,
)

@app.middleware("http")
async def api_rate_limit_and_headers(request: Request, call_next):
    if not request.url.path.startswith("/api/v1/"):
        return await call_next(request)

    now = time()
    window_start = now - 60
    limit = settings.API_RATE_LIMIT_PER_MINUTE
    client = request.client.host if request.client else "unknown"
    key = (client, request.url.path)
    bucket = rate_limit_buckets[key]

    while bucket and bucket[0] < window_start:
        bucket.popleft()

    remaining = max(limit - len(bucket), 0)
    reset = int(bucket[0] + 60) if bucket else int(now + 60)
    if remaining <= 0:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded"},
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset),
                "Retry-After": str(max(reset - int(now), 1)),
            },
        )

    bucket.append(now)
    response = await call_next(request)
    response.headers.setdefault("X-RateLimit-Limit", str(limit))
    response.headers.setdefault("X-RateLimit-Remaining", str(max(limit - len(bucket), 0)))
    response.headers.setdefault("X-RateLimit-Reset", str(reset))
    if request.method in {"POST", "PUT", "DELETE"}:
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api/v1/"):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.errors()},
        )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})


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

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(api_v1_posts.router)
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
        print(f"Database error: {e}")
        articles = []
    
    return templates.TemplateResponse(
        "home.html", 
        {
            "request": request, 
            "articles": articles,
            "current_user": current_user,
            "messages": []  # Empty messages list for FastAPI
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
