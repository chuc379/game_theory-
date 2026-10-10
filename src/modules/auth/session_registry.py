"""
In-memory registry binding a socket id to its authenticated session.

The gateway runs as a single process, so a plain dict is enough. If the gateway
is ever scaled horizontally this must move to a shared store (Redis).
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

ROLE_MC = "mc"
ROLE_PLAYER = "player"


class SessionRegistry:
    """Tracks which role a connected socket holds."""

    def __init__(self) -> None:
        self._sessions: Dict[str, dict] = {}

    def bind_mc(self, sid: str, username: str) -> None:
        self._sessions[sid] = {
            "role": ROLE_MC,
            "username": username,
            "player_id": None,
            "room_id": None,
        }
        logger.info(f"Socket {sid} authenticated as MC '{username}'")

    def bind_player(self, sid: str, player_id: str, room_id: str) -> None:
        session = self._sessions.setdefault(sid, {"role": ROLE_PLAYER})
        session["role"] = ROLE_PLAYER
        session["player_id"] = player_id
        session["room_id"] = room_id

    def get(self, sid: str) -> Optional[dict]:
        return self._sessions.get(sid)

    def is_mc(self, sid: str) -> bool:
        session = self._sessions.get(sid)
        return bool(session and session.get("role") == ROLE_MC)

    def mc_username(self, sid: str) -> Optional[str]:
        session = self._sessions.get(sid)
        if session and session.get("role") == ROLE_MC:
            return session.get("username")
        return None

    def player_id(self, sid: str) -> Optional[str]:
        session = self._sessions.get(sid)
        return session.get("player_id") if session else None

    def remove(self, sid: str) -> None:
        self._sessions.pop(sid, None)


session_registry = SessionRegistry()
