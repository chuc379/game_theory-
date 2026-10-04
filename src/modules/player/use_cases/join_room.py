"""
Join room use case - Business logic for player joining room
"""
import logging
from src.modules.player.domain.player_repository import IPlayerRepository
from src.modules.player.use_cases.player_factory import PlayerFactory

logger = logging.getLogger(__name__)


class JoinRoomUseCase:
    """Use case for player joining room"""

    def __init__(self, player_repository: IPlayerRepository):
        self.player_repo = player_repository
        self.player_factory = PlayerFactory()

    async def execute(
        self,
        room_id: str,
        player_name: str,
        socket_id: str,
        player_id: str = None,
    ) -> dict:
        """
        Join room use case logic
        
        Args:
            room_id: Room identifier
            player_name: Player name
            socket_id: Socket.io connection ID
            player_id: Stable client identity; reused when it already exists in the room
            
        Returns:
            dict with player data and status
        """
        try:
            existing = None
            if player_id:
                existing = await self.player_repo.find_by_id(room_id, player_id)

            if existing:
                existing.name = player_name.strip()
                existing.update_socket(socket_id)
                player = existing
            else:
                player = self.player_factory.create_player(
                    player_name, socket_id, player_id=player_id
                )


            # Validate
            if not player.is_valid():
                return {"success": False, "error": "Invalid player data"}

            # Save to repository
            await self.player_repo.save(room_id, player)

            logger.info(f"Player {player.player_id} joined room {room_id}")

            return {
                "success": True,
                "player": player.to_dict(),
                "message": f"Player {player_name} joined successfully",
            }
        except Exception as e:
            logger.error(f"Join room failed: {e}")
            return {"success": False, "error": str(e)}
