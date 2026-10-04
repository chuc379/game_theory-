"""
Player factory - Factory pattern for creating player instances
"""
import uuid
from typing import Optional
from src.modules.player.domain.player_entity import PlayerEntity


class PlayerFactory:
    """Factory for creating PlayerEntity instances"""

    @staticmethod
    def create_player(
        name: str, socket_id: str, player_id: Optional[str] = None
    ) -> PlayerEntity:
        """Create new player instance"""
        return PlayerEntity(
            player_id=player_id or str(uuid.uuid4()),
            socket_id=socket_id,
            name=name.strip(),
            is_online=True,
        )

    @staticmethod
    def create_from_session_data(session_data: dict) -> PlayerEntity:
        """Create player from session data"""
        return PlayerEntity(**session_data)
