"""
JWT access tokens for the MC role.

Tokens are stateless: everything needed to validate them (signature + expiry)
lives inside the token, so no database is required.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from config.settings import settings

logger = logging.getLogger(__name__)

MC_ROLE = "mc"


class TokenError(Exception):
    """Raised when a token cannot be created because config is missing."""


def create_access_token(username: str) -> str:
    """Sign a short-lived access token for an authenticated MC."""
    if not settings.JWT_SECRET:
        raise TokenError("JWT_SECRET is not configured")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": MC_ROLE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_access_token(token: Optional[str]) -> Optional[str]:
    """Return the MC username when the token is valid, otherwise None."""
    if not token or not settings.JWT_SECRET:
        return None
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.PyJWTError as e:
        logger.warning(f"Rejected JWT: {e}")
        return None
    if payload.get("role") != MC_ROLE:
        return None
    username = payload.get("sub")
    return username if isinstance(username, str) and username else None
