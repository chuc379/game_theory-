"""
In-memory registry binding a socket id to its authenticated session.

The gateway runs as a single process, so a plain dict is enough. If the gateway
is ever scaled horizontally this must move to a shared store (Redis).
"""
import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ROLE_MC = "mc"
ROLE_PLAYER = "player"


class SessionRegistry:
    """Tracks which role a connected socket holds."""

    def __init__(self) -> None:
        self._sessions: Dict[str, dict] = {}

    def bind_mc(self, sid: str, username: str) -> None:
        session = self._sessions.setdefault(sid, {})
        session.update(
            {
                "role": ROLE_MC,
                "username": username,
                "player_id": None,
                "room_id": None,
                "joined_at": time.time(),
            }
        )
        logger.info(f"Socket {sid} authenticated as MC '{username}'")

    def bind_device(self, sid: str, device_id: Optional[str]) -> None:
        if not device_id:
            return
        session = self._sessions.setdefault(sid, {"role": ROLE_PLAYER})
        session["device_id"] = device_id

    def device_id(self, sid: str) -> Optional[str]:
        session = self._sessions.get(sid)
        return session.get("device_id") if session else None

    def bind_player_token(self, sid: str, identity: dict) -> None:
        """Remember a verified player JWT for this socket."""
        session = self._sessions.setdefault(sid, {"role": ROLE_PLAYER})
        session["player_identity"] = identity
        if identity.get("device_id") and not session.get("device_id"):
            session["device_id"] = identity.get("device_id")

    def player_identity(self, sid: str) -> Optional[dict]:
        session = self._sessions.get(sid)
        return session.get("player_identity") if session else None

    def bind_player(self, sid: str, player_id: str, room_id: str) -> None:
        session = self._sessions.setdefault(sid, {"role": ROLE_PLAYER})
        session["role"] = ROLE_PLAYER
        session["player_id"] = player_id
        session["room_id"] = room_id
        session.setdefault("joined_at", time.time())
        session["spectator"] = False
        session.pop("spectator_reason", None)

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

    def player_sids(
        self, room_id: str, device_id: Optional[str] = None
    ) -> List[str]:
        """Player sockets currently bound to a room (oldest first)."""
        sids = []
        for sid, session in self._sessions.items():
            if session.get("role") != ROLE_PLAYER:
                continue
            if session.get("room_id") != room_id:
                continue
            if device_id is not None and session.get("device_id") != device_id:
                continue
            sids.append(sid)
        sids.sort(key=lambda sid: self._sessions[sid].get("joined_at") or 0)
        return sids

    def mark_spectator(self, sid: str, reason: str = "") -> None:
        session = self._sessions.get(sid)
        if not session:
            return
        session["spectator"] = True
        session["spectator_reason"] = reason
        session["player_id"] = None

    def is_spectator(self, sid: str) -> bool:
        session = self._sessions.get(sid)
        return bool(session and session.get("spectator"))

    def remove(self, sid: str) -> None:
        self._sessions.pop(sid, None)


session_registry = SessionRegistry()
