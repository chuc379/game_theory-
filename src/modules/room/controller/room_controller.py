"""
Room controller - API schema & handlers for room operations
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def validate_create_room(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate create room request"""
    if not data.get("room_id"):
        return False, "room_id is required"
    
    return True, ""


class RoomController:
    """Room controller - Handles room operations"""

    def __init__(self, room_repository):
        self.room_repo = room_repository

    async def list_rooms(self) -> list:
        """Get all active rooms"""
        try:
            rooms = await self.room_repo.get_all_rooms()
            return rooms or []
        except Exception as e:
            logger.error(f"Error listing rooms: {e}")
            return []

    async def save_room_info(self, room_id: str, info: dict) -> None:
        """Save room info"""
        try:
            await self.room_repo.save_info(room_id, info)
        except Exception as e:
            logger.error(f"Error saving room info: {e}")
            raise

    async def update_player_count(self, room_id: str) -> None:
        """Increment player count for room"""
        try:
            room_info = await self.room_repo.find_info(room_id)
            if room_info:
                room_info["player_count"] = room_info.get("player_count", 0) + 1
                await self.room_repo.save_info(room_id, room_info)
        except Exception as e:
            logger.error(f"Error updating player count: {e}")

    async def create_room(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create new room"""
        try:
            valid, error = validate_create_room(request)
            if not valid:
                return {"success": False, "error": error}
            
            room_info = {
                "room_id": request.get("room_id"),
                "current_round": 1,
                "status": "ACTIVE",
            }
            await self.room_repo.save_info(request.get("room_id"), room_info)
            return {
                "success": True,
                "message": "Room created successfully",
                "room": room_info,
            }
        except Exception as e:
            logger.error(f"Error creating room: {e}")
            return {"success": False, "error": str(e)}
