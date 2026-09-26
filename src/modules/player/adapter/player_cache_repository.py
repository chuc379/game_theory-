"""
Player repository implementation - Redis adapter
"""
import logging
from typing import Optional, List
from src.modules.player.domain.player_repository import IPlayerRepository
from src.modules.player.domain.player_entity import PlayerEntity
from src.shared.infrastructure.cache.redis_client import redis_client
from src.shared.constants import REDIS_ROOM_PLAYERS

logger = logging.getLogger(__name__)


class PlayerCacheRepository(IPlayerRepository):
    """Redis-based player repository"""

    def __init__(self, cache=redis_client):
        self.cache = cache

    def _get_key(self, room_id: str) -> str:
        return REDIS_ROOM_PLAYERS.format(room_id=room_id)

    async def save(self, room_id: str, player: PlayerEntity) -> None:
        """Save player to Redis hash"""
        try:
            key = self._get_key(room_id)
            await self.cache.hset(key, {player.player_id: player.to_dict()})
            logger.debug(f"Player {player.player_id} saved in room {room_id}")
        except Exception as e:
            logger.error(f"Failed to save player: {e}")
            raise

    async def find_by_id(self, room_id: str, player_id: str) -> Optional[PlayerEntity]:
        """Find player by ID"""
        try:
            key = self._get_key(room_id)
            data = await self.cache.hget_json(key, player_id)
            if data:
                return PlayerEntity(**data)
            return None
        except Exception as e:
            logger.error(f"Failed to find player: {e}")
            return None

    async def find_all_by_room(self, room_id: str) -> List[PlayerEntity]:
        """Find all players in room"""
        try:
            key = self._get_key(room_id)
            data = await self.cache.hgetall(key)
            return [PlayerEntity(**v) for v in data.values()]
        except Exception as e:
            logger.error(f"Failed to find players: {e}")
            return []

    async def delete(self, room_id: str, player_id: str) -> None:
        """Delete player from room"""
        try:
            key = self._get_key(room_id)
            await self.cache.hdel(key, player_id)
            logger.debug(f"Player {player_id} deleted from room {room_id}")
        except Exception as e:
            logger.error(f"Failed to delete player: {e}")
            raise

    async def count_by_room(self, room_id: str) -> int:
        """Count players in room"""
        try:
            key = self._get_key(room_id)
            data = await self.cache.hgetall(key)
            return len(data)
        except Exception as e:
            logger.error(f"Failed to count players: {e}")
            return 0
