"""
Round repository implementation - Redis adapter
"""
import logging
from typing import Optional, List
from src.modules.game_round.domain.round_repository import (
    IGuessRepository,
    IRoundResultRepository,
)
from src.shared.domain.entities import PlayerGuess, RoundResult, Winner
from src.shared.infrastructure.cache.redis_client import redis_client
from src.shared.constants import REDIS_ROUND_GUESSES, REDIS_ROUND_RESULT

logger = logging.getLogger(__name__)


class GuessCacheRepository(IGuessRepository):
    """Redis-based guess repository"""

    def __init__(self, cache=redis_client):
        self.cache = cache

    def _get_key(self, room_id: str, round_id: int) -> str:
        return REDIS_ROUND_GUESSES.format(room_id=room_id, round_id=round_id)

    async def save(self, room_id: str, round_id: int, guess: PlayerGuess) -> None:
        """Save guess to Redis hash"""
        try:
            key = self._get_key(room_id, round_id)
            await self.cache.hset(key, {guess.player_id: guess.to_dict()})
            logger.debug(f"Guess saved for player {guess.player_id} in round {round_id}")
        except Exception as e:
            logger.error(f"Failed to save guess: {e}")
            raise

    async def find_all(self, room_id: str, round_id: int) -> List[PlayerGuess]:
        """Find all guesses in round"""
        try:
            key = self._get_key(room_id, round_id)
            data = await self.cache.hgetall(key)
            return [PlayerGuess(**v) for v in data.values()]
        except Exception as e:
            logger.error(f"Failed to find guesses: {e}")
            return []

    async def delete_all(self, room_id: str, round_id: int) -> None:
        """Delete all guesses in round"""
        try:
            key = self._get_key(room_id, round_id)
            await self.cache.delete(key)
            logger.debug(f"All guesses deleted for round {round_id}")
        except Exception as e:
            logger.error(f"Failed to delete guesses: {e}")
            raise


class RoundResultCacheRepository(IRoundResultRepository):
    """Redis-based round result repository"""

    def __init__(self, cache=redis_client):
        self.cache = cache

    def _get_key(self, room_id: str, round_id: int) -> str:
        return REDIS_ROUND_RESULT.format(room_id=room_id, round_id=round_id)

    async def save(self, room_id: str, round_id: int, result: RoundResult) -> None:
        """Save round result to Redis"""
        try:
            key = self._get_key(room_id, round_id)
            await self.cache.set(key, result.to_dict())
            logger.debug(f"Round result saved for round {round_id}")
        except Exception as e:
            logger.error(f"Failed to save round result: {e}")
            raise

    async def find(self, room_id: str, round_id: int) -> Optional[RoundResult]:
        """Find round result"""
        try:
            key = self._get_key(room_id, round_id)
            data = await self.cache.get_json(key)
            if data:
                return RoundResult.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"Failed to find round result: {e}")
            return None
