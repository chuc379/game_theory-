"""
Score repository interface - Defines contract for survival score data access
"""
from abc import ABC, abstractmethod
from typing import Iterable, List, Optional

from src.shared.domain.scoring import PlayerScore


class IScoreRepository(ABC):
    """Score repository interface"""

    @abstractmethod
    async def get_all(self, room_id: str) -> List[PlayerScore]:
        pass

    @abstractmethod
    async def get(self, room_id: str, player_id: str) -> Optional[PlayerScore]:
        pass

    @abstractmethod
    async def save(self, room_id: str, score: PlayerScore) -> None:
        pass

    @abstractmethod
    async def save_many(self, room_id: str, scores: Iterable[PlayerScore]) -> None:
        pass

    @abstractmethod
    async def ensure_player(
        self, room_id: str, player_id: str, player_name: str
    ) -> PlayerScore:
        pass

    @abstractmethod
    async def ensure_players(self, room_id: str, players: Iterable) -> List[PlayerScore]:
        pass
