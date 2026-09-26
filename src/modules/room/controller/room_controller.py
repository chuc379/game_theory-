"""
Room controller - API schema & handlers for room operations
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Request/Response schemas
class CreateRoomRequest(BaseModel):
    """Create room request schema"""
    room_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "room_id": "CLB30",
            }
        }


class RoomInfoSchema(BaseModel):
    """Room info response schema"""
    room_id: str
    current_round: int
    status: str


class CreateRoomResponse(BaseModel):
    """Create room response"""
    success: bool
    message: str
    room: RoomInfoSchema = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Room created successfully",
                "room": {
                    "room_id": "CLB30",
                    "current_round": 1,
                    "status": "ACTIVE",
                },
            }
        }


class RoomController:
    """Room controller - Handles room operations"""

    def __init__(self, room_repository):
        self.room_repo = room_repository

    async def create_room(self, request: CreateRoomRequest) -> Dict[str, Any]:
        """Create new room"""
        try:
            room_info = {
                "room_id": request.room_id,
                "current_round": 1,
                "status": "ACTIVE",
            }
            await self.room_repo.save_info(request.room_id, room_info)
            return {
                "success": True,
                "message": "Room created successfully",
                "room": room_info,
            }
        except Exception as e:
            logger.error(f"Error creating room: {e}")
            return {"success": False, "error": str(e)}
