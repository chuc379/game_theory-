"""
Domain events - Event sourcing pattern
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


@dataclass
class DomainEvent:
    """Base domain event"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp() * 1000)
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


@dataclass
class PlayerSubmitGuessEvent(DomainEvent):
    """Event when player submits guess"""
    event_type: str = "PLAYER_SUBMIT_GUESS"


@dataclass
class CalculateRoundResultEvent(DomainEvent):
    """Event to calculate round result"""
    event_type: str = "CALCULATE_ROUND_RESULT"


@dataclass
class RoundResultReadyEvent(DomainEvent):
    """Event when round result is ready"""
    event_type: str = "ROUND_RESULT_READY"


@dataclass
class RoundResultFailedEvent(DomainEvent):
    """Event when round result could not be calculated"""
    event_type: str = "ROUND_RESULT_FAILED"


@dataclass
class PlayerJoinedEvent(DomainEvent):
    """Event when player joined"""
    event_type: str = "PLAYER_JOINED"


@dataclass
class PlayerLeftEvent(DomainEvent):
    """Event when player left"""
    event_type: str = "PLAYER_LEFT"
