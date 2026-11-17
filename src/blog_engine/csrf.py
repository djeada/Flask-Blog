import secrets

from fastapi import Request

CSRF_COOKIE_NAME = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def submitted_csrf_token(submitted: str | None) -> str:
    return submitted or ""


def csrf_matches(request: Request, submitted: str | None) -> bool:
    expected = request.cookies.get(CSRF_COOKIE_NAME)
    if not expected or not submitted:
        return False
    return secrets.compare_digest(expected, submitted)
