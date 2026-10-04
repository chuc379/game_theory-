"""
Domain entities - Core business objects
"""
from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime


@dataclass
class PlayerSession:
    """Player session entity"""
    player_id: str
    socket_id: str
    name: str
    is_online: bool = True
    joined_at: float = None

    def __post_init__(self):
        if self.joined_at is None:
            self.joined_at = datetime.now().timestamp() * 1000

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "socket_id": self.socket_id,
            "name": self.name,
            "is_online": self.is_online,
            "joined_at": self.joined_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "PlayerSession":
        return PlayerSession(**data)


@dataclass
class PlayerGuess:
    """Player guess entity"""
    player_id: str
    player_name: str
    guess_number: float
    submitted_at: float = None

    def __post_init__(self):
        if self.submitted_at is None:
            self.submitted_at = datetime.now().timestamp() * 1000

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "guess_number": self.guess_number,
            "submitted_at": self.submitted_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "PlayerGuess":
        return PlayerGuess(**data)


@dataclass
class Winner:
    """Winner entity"""
    player_id: str
    player_name: str
    guess_number: float
    difference: float

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "guess_number": self.guess_number,
            "difference": self.difference,
        }


@dataclass
class RoundResult:
    """Round result entity"""
    total_players: int
    average: float
    target: float
    winner: Winner
    force_calculate: bool = False
    calculated_at: float = None

    def __post_init__(self):
        if self.calculated_at is None:
            self.calculated_at = datetime.now().timestamp() * 1000

    def to_dict(self) -> dict:
        return {
            "total_players": self.total_players,
            "average": self.average,
            "target": self.target,
            "winner": self.winner.to_dict(),
            "force_calculate": self.force_calculate,
            "calculated_at": self.calculated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "RoundResult":
        data["winner"] = Winner(**data["winner"])
        return RoundResult(**data)


@dataclass
class GameRound:
    """Game round entity"""
    round_id: int
    status: str
    result: Optional[RoundResult] = None

    def to_dict(self) -> dict:
        return {
            "round_id": self.round_id,
            "status": self.status,
            "result": self.result.to_dict() if self.result else None,
        }
