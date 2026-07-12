from collections import defaultdict, deque
from contextlib import asynccontextmanager
from time import time

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from blog_engine.database import SessionLocal, create_blog_tables
from blog_engine.demo import seed_demo_content
from core.config import settings
from routers import api_v1_posts


rate_limit_buckets = defaultdict(deque)


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_blog_tables()
    if settings.BLOG_SEED_DEMO:
        with SessionLocal() as db:
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
    bucket = rate_limit_buckets[(client, request.url.path)]
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
    code = status.HTTP_400_BAD_REQUEST if request.url.path.startswith("/api/v1/") else status.HTTP_422_UNPROCESSABLE_ENTITY
    return JSONResponse(status_code=code, content={"detail": exc.errors()})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_v1_posts.router)


@app.get("/", include_in_schema=False)
async def root():
    return {"name": settings.APP_NAME, "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "healthy"}
