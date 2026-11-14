"""
JWT access tokens for the MC and player roles.

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
PLAYER_ROLE = "player"


class TokenError(Exception):
    """Raised when a token cannot be created because config is missing."""


def _encode(payload: dict) -> Optional[str]:
    if not settings.JWT_SECRET:
        logger.warning("JWT_SECRET is not configured; refusing to sign a token")
        return None
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


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


def create_player_token(
    player_id: str,
    room_id: str,
    player_name: str,
    device_id: Optional[str] = None,
) -> Optional[str]:
    """Sign a 2 hour identity token that lets a player rejoin as themselves.

    The token is bound to the room, so a token issued for one room cannot be
    replayed against another one.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": player_id,
        "role": PLAYER_ROLE,
        "room_id": room_id,
        "player_name": player_name,
        "device_id": device_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.PLAYER_JWT_EXPIRE_MINUTES),
    }
    return _encode(payload)


def _decode(token: Optional[str]) -> Optional[dict]:
    if not token or not settings.JWT_SECRET:
        return None
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.PyJWTError as e:
        logger.warning(f"Rejected JWT: {e}")
        return None


def verify_access_token(token: Optional[str]) -> Optional[str]:
    """Return the MC username when the token is valid, otherwise None."""
    payload = _decode(token)
    if not payload or payload.get("role") != MC_ROLE:
        return None
    username = payload.get("sub")
    return username if isinstance(username, str) and username else None


def verify_player_token(token: Optional[str]) -> Optional[dict]:
    """Return the player identity carried by a valid token, otherwise None."""
    payload = _decode(token)
    if not payload or payload.get("role") != PLAYER_ROLE:
        return None

    player_id = payload.get("sub")
    room_id = payload.get("room_id")
    if not isinstance(player_id, str) or not player_id:
        return None
    if not isinstance(room_id, str) or not room_id:
        return None

    return {
        "player_id": player_id,
        "room_id": room_id,
        "player_name": payload.get("player_name") or "Player",
        "device_id": payload.get("device_id"),
        "exp": payload.get("exp"),
    }
