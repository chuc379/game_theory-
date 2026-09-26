"""
Player domain entity
"""
from src.shared.domain.entities import PlayerSession


class PlayerEntity(PlayerSession):
    """Extended player entity with domain logic"""

    def mark_offline(self) -> None:
        """Mark player as offline"""
        self.is_online = False

    def update_socket(self, socket_id: str) -> None:
        """Update socket connection"""
        self.socket_id = socket_id
        self.is_online = True

    def is_valid(self) -> bool:
        """Validate player data"""
        return bool(self.player_id and self.name and len(self.name.strip()) > 0)
