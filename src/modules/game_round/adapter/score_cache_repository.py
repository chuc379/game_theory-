"""
Score repository implementation - Redis adapter for survival lives
"""
import logging
from typing import Iterable, List, Optional

from src.modules.game_round.domain.score_repository import IScoreRepository
from src.shared.constants import REDIS_ROOM_SCORES, STARTING_LIVES
from src.shared.domain.scoring import PlayerScore, RoomScoreboard
from src.shared.infrastructure.cache.redis_client import redis_client

logger = logging.getLogger(__name__)


class ScoreCacheRepository(IScoreRepository):
    """Redis-based survival score repository"""

    def __init__(self, cache=redis_client):
        self.cache = cache

    def _get_key(self, room_id: str) -> str:
        return REDIS_ROOM_SCORES.format(room_id=room_id)

    async def get_all(self, room_id: str) -> List[PlayerScore]:
        try:
            data = await self.cache.hgetall(self._get_key(room_id))
            return [
                PlayerScore.from_dict(value)
                for value in data.values()
                if isinstance(value, dict)
            ]
        except Exception as e:
            logger.error(f"Failed to load scores for room {room_id}: {e}")
            return []

    async def get(self, room_id: str, player_id: str) -> Optional[PlayerScore]:
        try:
            data = await self.cache.hget_json(self._get_key(room_id), player_id)
            return PlayerScore.from_dict(data) if data else None
        except Exception as e:
            logger.error(
                f"Failed to load score for player {player_id} in room {room_id}: {e}"
            )
            return None

    async def save(self, room_id: str, score: PlayerScore) -> None:
        try:
            await self.cache.hset(
                self._get_key(room_id), {score.player_id: score.to_dict()}
            )
        except Exception as e:
            logger.error(f"Failed to save score for {score.player_id}: {e}")
            raise

    async def save_many(self, room_id: str, scores: Iterable[PlayerScore]) -> None:
        mapping = {score.player_id: score.to_dict() for score in scores}
        if not mapping:
            return
        try:
            await self.cache.hset(self._get_key(room_id), mapping)
        except Exception as e:
            logger.error(f"Failed to save scoreboard for room {room_id}: {e}")
            raise

    async def delete(self, room_id: str, player_id: str) -> None:
        """Remove a player's survival score (used when a test link is demoted)"""
        try:
            await self.cache.hdel(self._get_key(room_id), player_id)
        except Exception as e:
            logger.error(
                f"Failed to delete score for player {player_id} in room {room_id}: {e}"
            )

    async def ensure_player(
        self, room_id: str, player_id: str, player_name: str
    ) -> PlayerScore:
        """Create a starting score for a player if it does not exist yet"""
        existing = await self.get(room_id, player_id)
        if existing:
            # Keep the display name in sync after a rejoin.
            if player_name and existing.player_name != player_name:
                existing.player_name = player_name
                await self.save(room_id, existing)
            return existing

        score = PlayerScore(
            player_id=player_id,
            player_name=player_name or "Player",
            total_points=STARTING_LIVES,
        )
        await self.save(room_id, score)
        return score

    async def ensure_players(self, room_id: str, players: Iterable) -> List[PlayerScore]:
        """Ensure every room player has a score entry and return the scoreboard"""
        existing = {score.player_id: score for score in await self.get_all(room_id)}
        changed = False

        for player in players:
            if isinstance(player, dict):
                player_id = player.get("player_id") or player.get("id")
                player_name = player.get("player_name") or player.get("name")
            else:
                player_id = getattr(player, "player_id", None)
                player_name = getattr(player, "name", None)

            if not player_id:
                continue

            if player_id in existing:
                if player_name and existing[player_id].player_name != player_name:
                    existing[player_id].player_name = player_name
                    changed = True
                continue

            existing[player_id] = PlayerScore(
                player_id=player_id,
                player_name=player_name or "Player",
                total_points=STARTING_LIVES,
            )
            changed = True

        if changed:
            await self.save_many(room_id, existing.values())

        return list(existing.values())

    async def get_ranking(self, room_id: str) -> List[dict]:
        scores = await self.get_all(room_id)
        return RoomScoreboard(room_id=room_id, players=scores).get_ranking()
