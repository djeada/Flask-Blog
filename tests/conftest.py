import os
import sys
from pathlib import Path

os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["BLOG_SEED_DEMO"] = "False"
os.environ["BLOG_DATABASE_URL"] = "sqlite://"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blog_engine.database import Base, SessionLocal, engine  # noqa: E402
from blog_engine.repository import ensure_role_defaults  # noqa: E402

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    ensure_role_defaults(db)
