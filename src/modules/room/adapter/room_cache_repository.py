"""
Room repository implementation - Redis adapter
"""
import logging
from typing import Optional, List
from src.shared.infrastructure.cache.redis_client import redis_client
from src.shared.constants import (
    REDIS_ROOM_CURRENT_ROUND,
    REDIS_ROOM_HISTORY,
    REDIS_ROOM_INFO,
    REDIS_ROOM_ROUND_STATUS,
    RoundStatus,
)

logger = logging.getLogger(__name__)


class RoomCacheRepository:
    """Redis-based room repository"""

    def __init__(self, cache=redis_client):
        self.cache = cache

    def _get_info_key(self, room_id: str) -> str:
        return REDIS_ROOM_INFO.format(room_id=room_id)

    def _get_history_key(self, room_id: str) -> str:
        return REDIS_ROOM_HISTORY.format(room_id=room_id)

    def _get_current_round_key(self, room_id: str) -> str:
        return REDIS_ROOM_CURRENT_ROUND.format(room_id=room_id)

    def _get_round_status_key(self, room_id: str) -> str:
        return REDIS_ROOM_ROUND_STATUS.format(room_id=room_id)

    async def get_current_round(self, room_id: str) -> int:
        """Get the authoritative round the room is currently on (0 = none started)"""
        try:
            key = self._get_current_round_key(room_id)
            value = await self.cache.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Failed to read current round: {e}")
            return 0

    async def next_round(self, room_id: str) -> int:
        """Atomically advance the room to the next round and return it"""
        try:
            key = self._get_current_round_key(room_id)
            round_id = await self.cache.incr(key)
            logger.info(f"Room {room_id} advanced to round {round_id}")
            return round_id
        except Exception as e:
            logger.error(f"Failed to advance round: {e}")
            raise

    async def get_round_status(self, room_id: str) -> str:
        """Get round status (WAITING / LOCKED / ENDED)"""
        try:
            key = self._get_round_status_key(room_id)
            return await self.cache.get(key) or RoundStatus.WAITING
        except Exception as e:
            logger.error(f"Failed to read round status: {e}")
            return RoundStatus.WAITING

    async def set_round_status(self, room_id: str, status: str) -> None:
        """Set round status"""
        try:
            key = self._get_round_status_key(room_id)
            await self.cache.set(key, status)
        except Exception as e:
            logger.error(f"Failed to write round status: {e}")
            raise

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

    async def get_all_rooms(self) -> List[dict]:
        """Get all active rooms"""
        try:
            # Find all room:info:* keys
            pattern = REDIS_ROOM_INFO.format(room_id="*")
            keys = await self.cache.keys(pattern)
            
            rooms = []
            for key in keys:
                room_data = await self.cache.get_json(key)
                if room_data:
                    rooms.append(room_data)
            
            return rooms
        except Exception as e:
            logger.error(f"Failed to get all rooms: {e}")
            return []
