"""
Round factory - Factory pattern for creating round instances
"""
from src.modules.game_round.domain.round_entity import RoundEntity
from src.shared.constants import RoundStatus


class RoundFactory:
    """Factory for creating RoundEntity instances"""

    @staticmethod
    def create_round(round_id: int) -> RoundEntity:
        """Create new round instance"""
        return RoundEntity(round_id=round_id, status=RoundStatus.WAITING, result=None)

    @staticmethod
    def create_from_data(data: dict) -> RoundEntity:
        """Create round from data"""
        return RoundEntity(**data)
