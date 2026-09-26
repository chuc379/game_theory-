"""
Repository interfaces - Abstraction for data access
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from src.shared.domain.entities import PlayerSession, PlayerGuess, RoundResult


class IPlayerRepository(ABC):
    """Player repository interface"""

    @abstractmethod
    async def save(self, room_id: str, player: PlayerSession) -> None:
        pass

    @abstractmethod
    async def find_by_id(self, room_id: str, player_id: str) -> Optional[PlayerSession]:
        pass

    @abstractmethod
    async def find_all_by_room(self, room_id: str) -> List[PlayerSession]:
        pass

    @abstractmethod
    async def delete(self, room_id: str, player_id: str) -> None:
        pass


class IGuessRepository(ABC):
    """Guess repository interface"""

    @abstractmethod
    async def save(self, room_id: str, round_id: int, guess: PlayerGuess) -> None:
        pass

    @abstractmethod
    async def find_all_by_round(
        self, room_id: str, round_id: int
    ) -> List[PlayerGuess]:
        pass

    @abstractmethod
    async def delete_all_by_round(self, room_id: str, round_id: int) -> None:
        pass


class IRoundResultRepository(ABC):
    """Round result repository interface"""

    @abstractmethod
    async def save(self, room_id: str, round_id: int, result: RoundResult) -> None:
        pass

    @abstractmethod
    async def find_by_round(
        self, room_id: str, round_id: int
    ) -> Optional[RoundResult]:
        pass


class IRoomRepository(ABC):
    """Room repository interface"""

    @abstractmethod
    async def save_info(self, room_id: str, info: dict) -> None:
        pass

    @abstractmethod
    async def find_info(self, room_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    async def add_to_history(self, room_id: str, result: dict) -> None:
        pass

    @abstractmethod
    async def get_history(self, room_id: str) -> List[dict]:
        pass
