"""
Round repository interface - Defines contract for round data access
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from src.shared.domain.entities import PlayerGuess, RoundResult


class IGuessRepository(ABC):
    """Guess repository interface"""

    @abstractmethod
    async def save(self, room_id: str, round_id: int, guess: PlayerGuess) -> None:
        pass

    @abstractmethod
    async def find_all(self, room_id: str, round_id: int) -> List[PlayerGuess]:
        pass

    @abstractmethod
    async def delete_all(self, room_id: str, round_id: int) -> None:
        pass


class IRoundResultRepository(ABC):
    """Round result repository interface"""

    @abstractmethod
    async def save(self, room_id: str, round_id: int, result: RoundResult) -> None:
        pass

    @abstractmethod
    async def find(self, room_id: str, round_id: int) -> Optional[RoundResult]:
        pass
