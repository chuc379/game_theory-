"""
Room repository implementation - Redis adapter
"""
import logging
from typing import Optional, List
from src.shared.infrastructure.cache.redis_client import redis_client
from src.shared.constants import REDIS_ROOM_INFO, REDIS_ROOM_HISTORY

logger = logging.getLogger(__name__)


class RoomCacheRepository:
    """Redis-based room repository"""

    def __init__(self, cache=redis_client):
        self.cache = cache

    def _get_info_key(self, room_id: str) -> str:
        return REDIS_ROOM_INFO.format(room_id=room_id)

    def _get_history_key(self, room_id: str) -> str:
        return REDIS_ROOM_HISTORY.format(room_id=room_id)

    async def save_info(self, room_id: str, info: dict) -> None:
        """Save room info"""
        try:
            key = self._get_info_key(room_id)
            await self.cache.set(key, info)
            logger.debug(f"Room info saved: {room_id}")
        except Exception as e:
            logger.error(f"Failed to save room info: {e}")
            raise

    async def find_info(self, room_id: str) -> Optional[dict]:
        """Find room info"""
        try:
            key = self._get_info_key(room_id)
            return await self.cache.get_json(key)
        except Exception as e:
            logger.error(f"Failed to find room info: {e}")
            return None

    async def add_to_history(self, room_id: str, result: dict) -> None:
        """Add result to room history"""
        try:
            key = self._get_history_key(room_id)
            await self.cache.lpush(key, result)
            logger.debug(f"Result added to history for room {room_id}")
        except Exception as e:
            logger.error(f"Failed to add to history: {e}")
            raise

    async def get_history(self, room_id: str) -> List[dict]:
        """Get room history"""
        try:
            key = self._get_history_key(room_id)
            return await self.cache.lrange(key)
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
