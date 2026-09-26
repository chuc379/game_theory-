"""
Player repository interface - Defines contract for player data access
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from src.modules.player.domain.player_entity import PlayerEntity


class IPlayerRepository(ABC):
    """Player repository interface"""

    @abstractmethod
    async def save(self, room_id: str, player: PlayerEntity) -> None:
        """Save or update player"""
        pass

    @abstractmethod
    async def find_by_id(self, room_id: str, player_id: str) -> Optional[PlayerEntity]:
        """Find player by ID"""
        pass

    @abstractmethod
    async def find_all_by_room(self, room_id: str) -> List[PlayerEntity]:
        """Find all players in room"""
        pass

    @abstractmethod
    async def delete(self, room_id: str, player_id: str) -> None:
        """Delete player from room"""
        pass

    @abstractmethod
    async def count_by_room(self, room_id: str) -> int:
        """Count players in room"""
        pass
