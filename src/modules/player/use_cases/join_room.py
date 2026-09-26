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

    async def execute(self, room_id: str, player_name: str, socket_id: str) -> dict:
        """
        Execute join room logic
        
        Args:
            room_id: Room identifier
            player_name: Player name
            socket_id: Socket.io connection ID
            
        Returns:
            dict with player data and status
        """
        try:
            # Create new player
            player = self.player_factory.create_player(player_name, socket_id)

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
