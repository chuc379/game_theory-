"""
Round controller - API schema & handlers for round operations
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def validate_submit_guess(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate submit guess request"""
    if not data.get("room_id"):
        return False, "room_id is required"
    if not data.get("round_id"):
        return False, "round_id is required"
    if not data.get("player_id"):
        return False, "player_id is required"
    if not data.get("player_name"):
        return False, "player_name is required"
    if data.get("guess_number") is None:
        return False, "guess_number is required"
    
    try:
        guess = float(data.get("guess_number"))
        if guess < 0 or guess > 100:
            return False, "guess_number must be between 0-100"
    except (ValueError, TypeError):
        return False, "guess_number must be a number"
    
    return True, ""


def validate_calculate_result(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate calculate result request"""
    if not data.get("room_id"):
        return False, "room_id is required"
    if not data.get("round_id"):
        return False, "round_id is required"
    
    return True, ""


class RoundController:
    """Round controller - Handles round operations"""

    def __init__(self, submit_guess_use_case, calculate_result_use_case):
        self.submit_guess_use_case = submit_guess_use_case
        self.calculate_result_use_case = calculate_result_use_case

    async def submit_guess(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Submit player guess"""
        try:
            valid, error = validate_submit_guess(request)
            if not valid:
                return {"success": False, "error": error}
            
            result = await self.submit_guess_use_case.execute(
                room_id=request.get("room_id"),
                round_id=int(request.get("round_id")),
                player_id=request.get("player_id"),
                player_name=request.get("player_name"),
                guess_number=float(request.get("guess_number")),
            )
            return result
        except Exception as e:
            logger.error(f"Error submitting guess: {e}")
            return {"success": False, "error": str(e)}

    async def calculate_result(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate round result"""
        try:
            valid, error = validate_calculate_result(request)
            if not valid:
                return {"success": False, "error": error}
            
            result = await self.calculate_result_use_case.execute(
                room_id=request.get("room_id"),
                round_id=int(request.get("round_id")),
            )
            return result
        except Exception as e:
            logger.error(f"Error calculating result: {e}")
            return {"success": False, "error": str(e)}
