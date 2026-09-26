"""
Room domain entity
"""


class RoomEntity:
    """Room entity"""

    def __init__(self, room_id: str, current_round: int = 1, status: str = "ACTIVE"):
        self.room_id = room_id
        self.current_round = current_round
        self.status = status

    def start_new_round(self) -> None:
        """Increment round number"""
        self.current_round += 1

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "current_round": self.current_round,
            "status": self.status,
        }

    @staticmethod
    def from_dict(data: dict) -> "RoomEntity":
        return RoomEntity(**data)
