"""
Scoring entities - Game scoring and ranking
"""
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class PlayerScore:
    """Player score in a room"""
    player_id: str
    player_name: str
    total_points: int = 0
    rounds_played: int = 0
    wins: int = 0
    updated_at: float = None

    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now().timestamp() * 1000

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "total_points": self.total_points,
            "rounds_played": self.rounds_played,
            "wins": self.wins,
            "updated_at": self.updated_at,
        }


@dataclass
class RoomScoreboard:
    """Room scoreboard - ranking of all players"""
    room_id: str
    players: List[PlayerScore]
    last_updated: float = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().timestamp() * 1000

    def get_ranking(self) -> List[Dict[str, Any]]:
        """Get sorted ranking by points"""
        sorted_players = sorted(
            self.players,
            key=lambda p: (-p.total_points, p.player_id)
        )
        return [
            {
                **p.to_dict(),
                "rank": idx + 1,
            }
            for idx, p in enumerate(sorted_players)
        ]

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "players": [p.to_dict() for p in self.players],
            "ranking": self.get_ranking(),
            "last_updated": self.last_updated,
        }
