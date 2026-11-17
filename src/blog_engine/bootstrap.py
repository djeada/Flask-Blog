import logging

from sqlalchemy.orm import Session

from blog_engine import repository
from blog_engine.models import BlogUser, Role
from blog_engine.security import hash_password

logger = logging.getLogger(__name__)


def ensure_initial_admin(db: Session, username: str, password: str) -> bool:
    """Create the first admin account when no admin exists.

    Returns True when an admin was created. Existing accounts are never
    modified and the password is never logged.
    """
    if not username.strip() or not password:
        return False
    if repository.count_admins(db) > 0:
        return False
    if repository.get_user_by_username(db, username.strip()) is not None:
        logger.warning("BLOG_ADMIN_USERNAME is set but that user already exists; leaving the account unchanged")
        return False

    db.add(
        BlogUser(
            username=username.strip(),
            password_hash=hash_password(password),
            role=Role.ADMIN,
        )
    )
    db.commit()
    logger.info("Created initial admin account %s", username.strip())
    return True
