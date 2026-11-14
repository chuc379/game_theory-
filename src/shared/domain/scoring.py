"""
Scoring entities - Survival mode lives, penalties and ranking
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.shared.constants import STARTING_LIVES


@dataclass
class PlayerScore:
    """Player score in a room (survival lives)"""

    player_id: str
    player_name: str
    total_points: int = STARTING_LIVES
    rounds_played: int = 0
    wins: int = 0
    eliminated: bool = False
    last_delta: int = 0
    updated_at: float = None

    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now().timestamp() * 1000
        # Defensive: never hold lives outside the valid range.
        if self.total_points < 0:
            self.total_points = 0
        if self.total_points == 0:
            self.eliminated = True

    @property
    def points(self) -> int:
        """Alias used by the frontend"""
        return self.total_points

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "total_points": self.total_points,
            "points": self.total_points,
            "rounds_played": self.rounds_played,
            "wins": self.wins,
            "eliminated": self.eliminated,
            "last_delta": self.last_delta,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "PlayerScore":
        payload = {
            "player_id": data.get("player_id"),
            "player_name": data.get("player_name") or data.get("name") or "Unknown",
            "total_points": int(
                data.get("total_points", data.get("points", STARTING_LIVES))
            ),
            "rounds_played": int(data.get("rounds_played", 0)),
            "wins": int(data.get("wins", 0)),
            "eliminated": bool(data.get("eliminated", False)),
            "last_delta": int(data.get("last_delta", 0)),
            "updated_at": data.get("updated_at"),
        }
        return PlayerScore(**payload)


@dataclass
class RoomScoreboard:
    """Room scoreboard - ranking of all players"""

    room_id: str
    players: List[PlayerScore]
    last_updated: float = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().timestamp() * 1000

    def get_ranking(self) -> List[Dict[str, Any]]:
        """Get sorted ranking: alive players first, then by remaining lives"""
        sorted_players = sorted(
            self.players,
            key=lambda p: (
                p.eliminated,
                -p.total_points,
                (p.player_name or "").lower(),
            ),
        )
        return [
            {
                **p.to_dict(),
                "rank": idx + 1,
            }
            for idx, p in enumerate(sorted_players)
        ]

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "players": [p.to_dict() for p in self.players],
            "ranking": self.get_ranking(),
            "last_updated": self.last_updated,
        }


def apply_survival_round(
    scores: List[PlayerScore],
    guesses_by_player: Dict[str, float],
    winner_guess: Optional[float],
    convergence: bool,
) -> Dict[str, Any]:
    """Apply the survival rules to a finished round.

    Rules:
      * Normal round: every player whose guess is not the winning guess loses a
        life. Players that did not submit count as wrong.
      * Converged round (target ~= 0): every player that picked 0 loses a life,
        everyone else is safe.

    Mutates ``scores`` in place and returns a summary that can be sent to the
    clients (scoreboard, eliminated players, game over state).
    """
    alive = [score for score in scores if not score.eliminated]
    correct_ids = set()

    # Eliminated players are spectators: they do not play this round, so they
    # must not keep showing the delta from the round that killed them.
    for score in scores:
        if score.eliminated:
            score.last_delta = 0

    if convergence:
        loser_ids = {
            player_id
            for player_id, guess in guesses_by_player.items()
            if guess == 0
        }
        rule = "convergence"
    elif winner_guess is None:
        # Nobody submitted: everyone still alive loses a life.
        loser_ids = {score.player_id for score in alive}
        rule = "no_submissions"
    else:
        correct_ids = {
            player_id
            for player_id, guess in guesses_by_player.items()
            if guess == winner_guess
        }
        loser_ids = {score.player_id for score in alive} - correct_ids
        rule = "closest_guess"

    eliminated_now: List[PlayerScore] = []

    for score in alive:
        score.rounds_played += 1

        if score.player_id in correct_ids:
            score.wins += 1

        if score.player_id in loser_ids:
            previous = score.total_points
            score.total_points = max(0, previous - 1)
            score.last_delta = score.total_points - previous
            if score.total_points == 0 and not score.eliminated:
                score.eliminated = True
                eliminated_now.append(score)
        else:
            score.last_delta = 0

        score.updated_at = datetime.now().timestamp() * 1000

    survivors = [score for score in scores if not score.eliminated]
    game_over = len(survivors) <= 1
    survivor = survivors[0] if game_over and len(survivors) == 1 else None

    return {
        "rule": rule,
        "convergence": convergence,
        "loser_ids": sorted(loser_ids),
        "correct_ids": sorted(correct_ids),
        "eliminated": [score.to_dict() for score in eliminated_now],
        "game_over": game_over,
        "survivor": survivor.to_dict() if survivor else None,
        "scoreboard": RoomScoreboard(
            room_id="",
            players=scores,
        ).get_ranking(),
    }
