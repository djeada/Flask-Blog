import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.config import (  # noqa: E402
    DEFAULT_SECRET_KEY,
    MIN_SECRET_KEY_LENGTH,
    ProductionConfigError,
    Settings,
    validate_production_settings,
)
from core.config import settings as global_settings  # noqa: E402
from main import app  # noqa: E402

STRONG_SECRET = "a" * MIN_SECRET_KEY_LENGTH


def production_settings(**overrides) -> Settings:
    values = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": STRONG_SECRET,
        "SESSION_COOKIE_SECURE": True,
        "DEBUG": False,
        "BLOG_SEED_DEMO": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_production_rejects_default_secret():
    with pytest.raises(ProductionConfigError, match="insecure default"):
        validate_production_settings(production_settings(SECRET_KEY=DEFAULT_SECRET_KEY))


def test_production_rejects_short_secret():
    with pytest.raises(ProductionConfigError, match="too short"):
        validate_production_settings(production_settings(SECRET_KEY="short"))


def test_production_rejects_debug():
    with pytest.raises(ProductionConfigError, match="DEBUG"):
        validate_production_settings(production_settings(DEBUG=True))


def test_production_rejects_insecure_cookies():
    with pytest.raises(ProductionConfigError, match="SESSION_COOKIE_SECURE"):
        validate_production_settings(production_settings(SESSION_COOKIE_SECURE=False))


def test_production_rejects_demo_seeding():
    with pytest.raises(ProductionConfigError, match="BLOG_SEED_DEMO"):
        validate_production_settings(production_settings(BLOG_SEED_DEMO=True))


def test_production_accepts_hardened_settings():
    validate_production_settings(production_settings())


def test_validation_collects_all_problems():
    with pytest.raises(ProductionConfigError) as exc_info:
        validate_production_settings(
            production_settings(DEBUG=True, SESSION_COOKIE_SECURE=False, BLOG_SEED_DEMO=True)
        )
    message = str(exc_info.value)
    assert "DEBUG" in message
    assert "SESSION_COOKIE_SECURE" in message
    assert "BLOG_SEED_DEMO" in message


def test_development_mode_allows_defaults():
    validate_production_settings(Settings(ENVIRONMENT="development"))


def test_production_startup_fails_fast(monkeypatch):
    monkeypatch.setattr(global_settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(global_settings, "SECRET_KEY", DEFAULT_SECRET_KEY)

    with pytest.raises(ProductionConfigError):
        with TestClient(app):
            pass
