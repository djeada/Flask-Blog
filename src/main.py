import logging
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from time import time

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from blog_engine.database import SessionLocal, create_blog_tables
from blog_engine.demo import seed_demo_content
from blog_engine.repository import ensure_role_defaults
from core.config import DEFAULT_SECRET_KEY, settings
from routers import api_v1_auth, api_v1_posts, api_v1_roles, api_v1_users, web

logger = logging.getLogger(__name__)
rate_limit_buckets = defaultdict(deque)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.SECRET_KEY == DEFAULT_SECRET_KEY:
        logger.warning("SECRET_KEY is the insecure default; set a strong SECRET_KEY outside local development")
    create_blog_tables()
    with SessionLocal() as db:
        ensure_role_defaults(db)
        if settings.BLOG_SEED_DEMO:
            seed_demo_content(db)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="A small role-aware blog posts API",
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
    bucket = rate_limit_buckets[client]
    while bucket and bucket[0] < window_start:
        bucket.popleft()

    remaining = max(limit - len(bucket), 0)
    reset = int(bucket[0] + 60) if bucket else int(now + 60)
    headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(max(remaining - 1, 0)),
        "X-RateLimit-Reset": str(reset),
    }
    if remaining <= 0:
        if not bucket:
            rate_limit_buckets.pop(client, None)
        headers.update({"X-RateLimit-Remaining": "0", "Retry-After": str(max(reset - int(now), 1))})
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded"},
            headers=headers,
        )

    bucket.append(now)
    response = await call_next(request)
    for name, value in headers.items():
        response.headers.setdefault(name, value)
    if request.method in {"POST", "PUT", "DELETE"}:
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    is_api = request.url.path.startswith("/api/v1/")
    code = status.HTTP_400_BAD_REQUEST if is_api else status.HTTP_422_UNPROCESSABLE_ENTITY
    return JSONResponse(
        status_code=code, content={"detail": jsonable_encoder(exc.errors())}
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == status.HTTP_404_NOT_FOUND and not request.url.path.startswith("/api/"):
        return web.templates.TemplateResponse(
            "404.html",
            {
                "request": request,
                "principal": None,
                "app_name": settings.APP_NAME,
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(web.STATIC_DIR)), name="static")
app.include_router(api_v1_auth.router)
app.include_router(api_v1_roles.router)
app.include_router(api_v1_posts.router)
app.include_router(api_v1_users.router)
app.include_router(web.router)


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "healthy"}
