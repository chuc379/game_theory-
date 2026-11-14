"""
Room session policy - Strategy + Factory pattern.

Every room keeps a small JSON ``config`` dict. The dict is normalised once (so
old rooms and hand written payloads are safe) and a concrete strategy then
decides:

* whether the same device may open another player link, and
* whether the room has to fall back to a single link when a round starts.

Adding a new policy only means adding a class to ``SessionPolicyFactory``; the
gateway never needs to know which concrete policy a room uses.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

SESSION_MODE_MULTI_LINK = "multi_link"
SESSION_MODE_SINGLE_LINK = "single_link"
SESSION_MODES = (SESSION_MODE_MULTI_LINK, SESSION_MODE_SINGLE_LINK)

MAX_PLAYER_LINKS_LIMIT = 20

DEFAULT_ROOM_CONFIG: Dict[str, object] = {
    "session_mode": SESSION_MODE_MULTI_LINK,
    "max_player_links": 6,
    "lock_on_round_start": True,
}


def _as_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def normalize_room_config(raw: Optional[dict]) -> dict:
    """Merge a room config dict with the defaults and coerce every field."""
    raw = raw if isinstance(raw, dict) else {}

    mode = raw.get("session_mode")
    if mode not in SESSION_MODES:
        # Backwards compatibility with the earlier ``allow_multi_link`` flag.
        allow_multi = raw.get("allow_multi_link")
        mode = (
            SESSION_MODE_MULTI_LINK
            if allow_multi is None or _as_bool(allow_multi, True)
            else SESSION_MODE_SINGLE_LINK
        )

    try:
        max_links = int(
            raw.get("max_player_links", DEFAULT_ROOM_CONFIG["max_player_links"])
        )
    except (TypeError, ValueError):
        max_links = int(DEFAULT_ROOM_CONFIG["max_player_links"])
    max_links = max(1, min(MAX_PLAYER_LINKS_LIMIT, max_links))

    lock_on_start = _as_bool(
        raw.get("lock_on_round_start"),
        bool(DEFAULT_ROOM_CONFIG["lock_on_round_start"]),
    )

    return {
        "session_mode": mode,
        "max_player_links": max_links,
        "lock_on_round_start": lock_on_start,
    }


@dataclass
class SessionContext:
    """Everything a policy needs to make a decision."""

    role: str = "player"
    device_id: Optional[str] = None
    existing_sids: List[str] = field(default_factory=list)
    round_active: bool = False


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str = ""
    code: str = ""
    limit: int = 0


class SessionPolicy(ABC):
    """Base strategy: one link limit per device for players."""

    mode = "base"

    def __init__(self, config: Optional[dict] = None):
        self.config = normalize_room_config(config)

    @abstractmethod
    def decide(self, ctx: SessionContext) -> PolicyDecision:
        raise NotImplementedError

    def link_limit(self, ctx: SessionContext) -> int:
        return int(self.config.get("max_player_links", 1))

    def locks_on_round_start(self) -> bool:
        return bool(self.config.get("lock_on_round_start", True))


class MultiLinkSessionPolicy(SessionPolicy):
    """Testing mode: a device may hold several player links.

    Optionally the room is locked down to one link per device once a round is
    live (``lock_on_round_start``), which is what a real match needs.
    """

    mode = SESSION_MODE_MULTI_LINK

    def link_limit(self, ctx: SessionContext) -> int:
        if ctx.round_active and self.locks_on_round_start():
            return 1
        return int(self.config.get("max_player_links", 1))

    def decide(self, ctx: SessionContext) -> PolicyDecision:
        # The MC is exempt: one machine may host the MC tab and player tabs.
        if ctx.role != "player" or not ctx.device_id:
            return PolicyDecision(True)

        limit = self.link_limit(ctx)
        used = len(ctx.existing_sids)
        if used >= limit:
            if limit == 1 and ctx.round_active:
                reason = (
                    "Phòng đang trong ván đấu: mỗi máy chỉ được dùng 1 link "
                    "người chơi. Hãy đóng các tab còn lại."
                )
                code = "device_link_limit_round"
            else:
                reason = (
                    f"Máy này đã mở {used} link người chơi "
                    f"(tối đa {limit})."
                )
                code = "device_link_limit"
            return PolicyDecision(False, reason, code, limit)

        return PolicyDecision(True, limit=limit)


class SingleLinkSessionPolicy(SessionPolicy):
    """Match mode: exactly one player link per device, at all times."""

    mode = SESSION_MODE_SINGLE_LINK

    def link_limit(self, ctx: SessionContext) -> int:
        return 1

    def decide(self, ctx: SessionContext) -> PolicyDecision:
        if ctx.role != "player" or not ctx.device_id:
            return PolicyDecision(True, limit=1)

        if ctx.existing_sids:
            return PolicyDecision(
                False,
                "Phòng này chỉ cho phép 1 link người chơi trên mỗi máy.",
                "device_link_limit",
                1,
            )
        return PolicyDecision(True, limit=1)


class SessionPolicyFactory:
    """Map a room config dict to a concrete session policy."""

    _strategies = {
        SESSION_MODE_MULTI_LINK: MultiLinkSessionPolicy,
        SESSION_MODE_SINGLE_LINK: SingleLinkSessionPolicy,
    }

    @classmethod
    def create(cls, config: Optional[dict]) -> SessionPolicy:
        normalized = normalize_room_config(config)
        strategy = cls._strategies.get(
            normalized["session_mode"], MultiLinkSessionPolicy
        )
        return strategy(normalized)

    @classmethod
    def describe(cls, config: Optional[dict]) -> dict:
        """Human friendly summary stored next to the public room data."""
        normalized = normalize_room_config(config)
        mode = normalized["session_mode"]
        return {
            **normalized,
            "label": (
                "Nhiều link / máy (test)"
                if mode == SESSION_MODE_MULTI_LINK
                else "1 link / máy"
            ),
        }
