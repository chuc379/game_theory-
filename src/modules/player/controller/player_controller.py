"""
Player controller - API schema & handlers for player operations
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def validate_join_room(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate join room request"""
    if not data.get("room_id"):
        return False, "room_id is required"
    if not data.get("player_name"):
        return False, "player_name is required"
    if not data.get("socket_id"):
        return False, "socket_id is required"
    
    player_name = str(data.get("player_name", "")).strip()
    if len(player_name) == 0 or len(player_name) > 100:
        return False, "player_name must be 1-100 characters"

    player_id = data.get("player_id")
    if player_id is not None and not str(player_id).strip():
        return False, "player_id must be a non-empty string"
    
    return True, ""


class PlayerController:
    """Player controller - Handles player operations"""

    def __init__(self, join_room_use_case):
        self.join_room_use_case = join_room_use_case

    async def join_room(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Player joins room"""
        try:
            valid, error = validate_join_room(request)
            if not valid:
                return {"success": False, "error": error}
            
            result = await self.join_room_use_case.execute(
                room_id=request.get("room_id"),
                player_name=request.get("player_name"),
                socket_id=request.get("socket_id"),
                player_id=request.get("player_id") or None,
            )
            return result
        except Exception as e:
            logger.error(f"Error joining room: {e}")
            return {"success": False, "error": str(e)}
