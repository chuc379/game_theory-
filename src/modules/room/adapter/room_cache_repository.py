"""
Room repository implementation - Redis adapter
"""
import logging
from typing import Optional, List
from src.shared.infrastructure.cache.redis_client import redis_client
from src.shared.constants import (
    REDIS_ROOMS_INDEX,
    REDIS_ROOM_CURRENT_ROUND,
    REDIS_ROOM_HISTORY,
    REDIS_ROOM_INFO,
    REDIS_ROOM_PLAYERS,
    REDIS_ROOM_ROUND_STATUS,
    REDIS_ROOM_SCORES,
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
        """Save room info and keep the room index in sync"""
        try:
            key = self._get_info_key(room_id)
            await self.cache.set(key, info)
            await self.add_to_index(room_id)
            logger.debug(f"Room info saved: {room_id}")
        except Exception as e:
            logger.error(f"Failed to save room info: {e}")
            raise

    async def update_info(self, room_id: str, patch: dict) -> Optional[dict]:
        """Merge a patch into the stored room info and return the result"""
        info = await self.find_info(room_id)
        if not info:
            return None
        info.update(patch or {})
        info["room_id"] = room_id
        await self.save_info(room_id, info)
        return info

    async def find_info(self, room_id: str) -> Optional[dict]:
        """Find room info"""
        try:
            key = self._get_info_key(room_id)
            return await self.cache.get_json(key)
        except Exception as e:
            logger.error(f"Failed to find room info: {e}")
            return None

    async def room_exists(self, room_id: str) -> bool:
        try:
            return bool(await self.cache.exists(self._get_info_key(room_id)))
        except Exception as e:
            logger.error(f"Failed to check room {room_id}: {e}")
            return False

    async def add_to_index(self, room_id: str) -> None:
        try:
            await self.cache.sadd(REDIS_ROOMS_INDEX, room_id)
        except Exception as e:
            logger.warning(f"Could not index room {room_id}: {e}")

    async def remove_from_index(self, room_id: str) -> None:
        try:
            await self.cache.srem(REDIS_ROOMS_INDEX, room_id)
        except Exception as e:
            logger.warning(f"Could not unindex room {room_id}: {e}")

    async def delete_room(self, room_id: str) -> bool:
        """Delete every key that belongs to a room (info, players, scores, rounds)"""
        keys = [
            self._get_info_key(room_id),
            self._get_history_key(room_id),
            self._get_current_round_key(room_id),
            self._get_round_status_key(room_id),
            REDIS_ROOM_PLAYERS.format(room_id=room_id),
            REDIS_ROOM_SCORES.format(room_id=room_id),
        ]
        try:
            round_keys = await self.cache.keys(f"room:{room_id}:round:*")
            keys.extend(round_keys or [])
        except Exception as e:
            logger.warning(f"Could not enumerate round keys for room {room_id}: {e}")

        try:
            await self.cache.delete_many(*keys)
            await self.remove_from_index(room_id)
            logger.info(f"Room {room_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete room {room_id}: {e}")
            return False

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

    async def _room_ids(self) -> List[str]:
        """Room ids from the index, with a KEYS fallback for legacy data."""
        room_ids = set()
        try:
            room_ids.update(await self.cache.smembers(REDIS_ROOMS_INDEX))
        except Exception as e:
            logger.warning(f"Could not read room index: {e}")

        try:
            pattern = REDIS_ROOM_INFO.format(room_id="*")
            for key in await self.cache.keys(pattern):
                parts = key.split(":")
                if len(parts) >= 2 and parts[1]:
                    room_ids.add(parts[1])
        except Exception as e:
            logger.warning(f"Could not scan room keys: {e}")

        return sorted(room_ids)

    async def get_all_rooms(self) -> List[dict]:
        """Get every room that still has an info record"""
        try:
            rooms = []
            for room_id in await self._room_ids():
                info = await self.find_info(room_id)
                if info:
                    rooms.append(info)
            return rooms
        except Exception as e:
            logger.error(f"Failed to get all rooms: {e}")
            return []
