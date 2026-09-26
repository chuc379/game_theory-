"""
Round controller - API schema & handlers for round operations
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Request/Response schemas
class SubmitGuessRequest(BaseModel):
    """Submit guess request schema"""
    room_id: str
    round_id: int
    player_id: str
    player_name: str
    guess_number: float = Field(..., ge=0, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "room_id": "CLB30",
                "round_id": 1,
                "player_id": "usr_abc123",
                "player_name": "Nguyễn Văn A",
                "guess_number": 22.5,
            }
        }


class CalculateResultRequest(BaseModel):
    """Calculate result request schema"""
    room_id: str
    round_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "room_id": "CLB30",
                "round_id": 1,
            }
        }


class GuessResponseSchema(BaseModel):
    """Guess response schema"""
    player_id: str
    player_name: str
    guess_number: float
    submitted_at: float


class WinnerSchema(BaseModel):
    """Winner schema"""
    player_id: str
    player_name: str
    guess_number: float
    difference: float


class RoundResultSchema(BaseModel):
    """Round result response schema"""
    total_players: int
    average: float
    target: float
    winner: WinnerSchema
    calculated_at: float


class SubmitGuessResponse(BaseModel):
    """Submit guess response"""
    success: bool
    message: str
    guess: GuessResponseSchema = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Guess submitted successfully",
                "guess": {
                    "player_id": "usr_abc123",
                    "player_name": "Nguyễn Văn A",
                    "guess_number": 22.5,
                    "submitted_at": 1727337039000,
                },
            }
        }


class CalculateResultResponse(BaseModel):
    """Calculate result response"""
    success: bool
    message: str
    result: RoundResultSchema = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Round 1 completed",
                "result": {
                    "total_players": 30,
                    "average": 45.5,
                    "target": 30.33,
                    "winner": {
                        "player_id": "usr_xyz789",
                        "player_name": "Trần Thị B",
                        "guess_number": 30.0,
                        "difference": 0.33,
                    },
                    "calculated_at": 1727337090000,
                },
            }
        }


class RoundController:
    """Round controller - Handles round operations"""

    def __init__(self, submit_guess_use_case, calculate_result_use_case):
        self.submit_guess_use_case = submit_guess_use_case
        self.calculate_result_use_case = calculate_result_use_case

    async def submit_guess(self, request: SubmitGuessRequest) -> Dict[str, Any]:
        """Submit player guess"""
        try:
            result = await self.submit_guess_use_case.execute(
                room_id=request.room_id,
                round_id=request.round_id,
                player_id=request.player_id,
                player_name=request.player_name,
                guess_number=request.guess_number,
            )
            return result
        except Exception as e:
            logger.error(f"Error submitting guess: {e}")
            return {"success": False, "error": str(e)}

    async def calculate_result(self, request: CalculateResultRequest) -> Dict[str, Any]:
        """Calculate round result"""
        try:
            result = await self.calculate_result_use_case.execute(
                room_id=request.room_id,
                round_id=request.round_id,
            )
            return result
        except Exception as e:
            logger.error(f"Error calculating result: {e}")
            return {"success": False, "error": str(e)}
