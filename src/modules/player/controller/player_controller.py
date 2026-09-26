"""
Player controller - API schema & handlers for player operations
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Request/Response schemas
class JoinRoomRequest(BaseModel):
    """Join room request schema"""
    room_id: str
    player_name: str = Field(..., min_length=1, max_length=100)
    socket_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "room_id": "CLB30",
                "player_name": "Nguyễn Văn A",
                "socket_id": "socket_12345",
            }
        }


class PlayerSessionSchema(BaseModel):
    """Player session response schema"""
    player_id: str
    socket_id: str
    name: str
    is_online: bool
    joined_at: float


class JoinRoomResponse(BaseModel):
    """Join room response"""
    success: bool
    message: str
    player: PlayerSessionSchema = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Player Nguyễn Văn A joined successfully",
                "player": {
                    "player_id": "usr_abc123",
                    "socket_id": "socket_12345",
                    "name": "Nguyễn Văn A",
                    "is_online": True,
                    "joined_at": 1727337000000,
                },
            }
        }


class PlayerController:
    """Player controller - Handles player operations"""

    def __init__(self, join_room_use_case):
        self.join_room_use_case = join_room_use_case

    async def join_room(self, request: JoinRoomRequest) -> Dict[str, Any]:
        """Player joins room"""
        try:
            result = await self.join_room_use_case.execute(
                room_id=request.room_id,
                player_name=request.player_name,
                socket_id=request.socket_id,
            )
            return result
        except Exception as e:
            logger.error(f"Error joining room: {e}")
            return {"success": False, "error": str(e)}
