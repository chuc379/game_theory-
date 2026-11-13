"""
Main application entry point - Socket.io gateway server (Starlette)
"""
import logging
import os
from contextlib import asynccontextmanager
from socketio import ASGIApp
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
from socketio.exceptions import ConnectionRefusedError
from starlette.requests import Request
from config.settings import settings
from src.shared.infrastructure.socket_io.socket_gateway import socket_gateway
from src.shared.infrastructure.cache.redis_client import redis_client
from src.shared.infrastructure.messaging.rabbitmq_client import rabbitmq_client

# Authentication (MC login)
from src.modules.auth.service import auth_service
from src.modules.auth.tokens import verify_access_token
from src.modules.auth.session_registry import session_registry

# Initialize repositories
from src.modules.player.adapter.player_cache_repository import PlayerCacheRepository
from src.modules.game_round.adapter.round_cache_repository import (
    GuessCacheRepository,
    RoundResultCacheRepository,
)
from src.modules.game_round.adapter.score_cache_repository import ScoreCacheRepository
from src.modules.room.adapter.room_cache_repository import RoomCacheRepository
from src.shared.domain.scoring import RoomScoreboard

# Initialize use cases
from src.modules.player.use_cases.join_room import JoinRoomUseCase
from src.modules.game_round.use_cases.submit_guess import SubmitGuessUseCase
from src.modules.game_round.use_cases.calculate_result import CalculateResultUseCase

# Initialize controllers
from src.modules.player.controller.player_controller import PlayerController
from src.modules.game_round.controller.round_controller import RoundController
from src.modules.room.controller.room_controller import RoomController

# Message publisher
from src.shared.infrastructure.messaging.message_publisher import message_publisher
from src.shared.infrastructure.messaging.event_consumer import EventConsumer
from src.shared.constants import (
    QUEUE_GATEWAY_ROUND_RESULTS,
    QUEUE_WORKER_CALCULATE_RESULTS,
    ROUND_DURATION_SECONDS,
    ROUTING_KEY_ROUND_CALCULATE,
    ROUTING_KEY_ROUND_RESULT_FAILED,
    ROUTING_KEY_ROUND_RESULT_READY,
    STARTING_LIVES,
    RoundStatus,
)

logger = logging.getLogger(__name__)


class GameApplication:
    """Main game application"""

    def __init__(self):
        self.player_controller = None
        self.round_controller = None
        self.room_controller = None
        self.player_repo = None
        self.guess_repo = None
        self.result_repo = None
        self.score_repo = None
        self.event_consumer = None
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize application"""
        if self.initialized:
            return

        try:
            # Connect to Redis
            await redis_client.connect()
            logger.info("Connected to Redis")

            # Connect to RabbitMQ
            rabbitmq_client.connect()
            logger.info("Connected to RabbitMQ")

            # Setup controllers with repositories and use cases
            self._setup_controllers()

            # Setup Socket.io handlers
            self.setup_socket_handlers()

            # Setup broker subscriptions
            await self._setup_event_consumer()

            # Buffer calculate requests even when the worker service is down so
            # they are replayed instead of dropped.
            message_publisher.ensure_queue(
                QUEUE_WORKER_CALCULATE_RESULTS, [ROUTING_KEY_ROUND_CALCULATE]
            )

            logger.info("Application initialized successfully")
            self.initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise

    def _setup_controllers(self) -> None:
        """Setup controllers"""
        # Player
        self.player_repo = PlayerCacheRepository()
        join_room_use_case = JoinRoomUseCase(self.player_repo)
        self.player_controller = PlayerController(join_room_use_case)

        # Room
        room_repo = RoomCacheRepository()
        self.room_controller = RoomController(room_repo)

        # Game Round
        self.guess_repo = GuessCacheRepository()
        self.result_repo = RoundResultCacheRepository()
        self.score_repo = ScoreCacheRepository()
        submit_guess_use_case = SubmitGuessUseCase(self.guess_repo)
        calculate_result_use_case = CalculateResultUseCase(
            self.guess_repo,
            self.result_repo,
            self.score_repo,
            self.player_repo,
        )
        self.round_controller = RoundController(
            submit_guess_use_case, calculate_result_use_case, room_repo
        )

    async def _setup_event_consumer(self) -> None:
        """Subscribe the gateway to the events it owns"""
        self.event_consumer = EventConsumer()

        self.event_consumer.subscribe(
            QUEUE_GATEWAY_ROUND_RESULTS,
            ROUTING_KEY_ROUND_RESULT_READY,
            self.on_round_result_ready_event,
        )
        self.event_consumer.subscribe(
            QUEUE_GATEWAY_ROUND_RESULTS,
            ROUTING_KEY_ROUND_RESULT_FAILED,
            self.on_round_result_failed_event,
        )

        await self.event_consumer.start()

    async def _build_room_state(self, room_id: str) -> dict:
        """Authoritative snapshot of a room: players, lives and submissions.

        Both the MC and the players use this instead of trying to reconstruct
        game state from individual events, which is what made the MC list stale.
        """
        players = await self.player_repo.find_all_by_room(room_id)
        scores = await self.score_repo.ensure_players(room_id, players)
        score_map = {score.player_id: score for score in scores}

        current_round = await self.room_controller.get_current_round(room_id)
        round_status = await self.room_controller.get_round_status(room_id)

        submitted_ids = set()
        if current_round > 0:
            guesses = await self.guess_repo.find_all(room_id, current_round)
            submitted_ids = {guess.player_id for guess in guesses}

        player_entries = []
        for player in players:
            score = score_map.get(player.player_id)
            player_entries.append(
                {
                    "player_id": player.player_id,
                    "player_name": player.name,
                    "socket_id": player.socket_id,
                    "is_online": player.is_online,
                    "submitted": player.player_id in submitted_ids,
                    "points": score.total_points if score else STARTING_LIVES,
                    "eliminated": score.eliminated if score else False,
                    "rounds_played": score.rounds_played if score else 0,
                    "wins": score.wins if score else 0,
                    "last_delta": score.last_delta if score else 0,
                }
            )

        scoreboard = RoomScoreboard(
            room_id=room_id,
            players=list(score_map.values()),
        ).get_ranking()

        return {
            "room_id": room_id,
            "current_round": current_round,
            "round_status": round_status,
            "players": player_entries,
            "scoreboard": scoreboard,
            "started_lives": STARTING_LIVES,
        }

    async def _broadcast_room_state(self, room_id: str, skip_sid: str = None) -> dict:
        """Push the authoritative room state to every client in the room"""
        try:
            state = await self._build_room_state(room_id)
            await socket_gateway.emit_async(
                "room_state",
                state,
                to=f"room_{room_id}",
                skip_sid=skip_sid,
            )
            return state
        except Exception as e:
            logger.error(f"Failed to broadcast room state for {room_id}: {e}", exc_info=True)
            return {}

    async def _refresh_player_count(self, room_id: str) -> None:
        """Store the real number of players on the room record"""
        try:
            players = await self.player_repo.find_all_by_room(room_id)
            info = await self.room_controller.room_repo.find_info(room_id) or {}
            info["room_id"] = room_id
            info["player_count"] = len(players)
            await self.room_controller.room_repo.save_info(room_id, info)
        except Exception as e:
            logger.warning(f"Failed to refresh player count for room {room_id}: {e}")

    async def on_round_result_ready_event(self, event: dict) -> None:
        """Handle computed round result coming back from the worker"""
        room_id = event.get("room_id")
        round_id = event.get("round_id")
        if not room_id or round_id is None:
            logger.error(f"Malformed round result event: {event}")
            return

        await self.room_controller.end_round(room_id)
        await socket_gateway.emit_async(
            "round_result_ready",
            {
                "room_id": room_id,
                "round_id": round_id,
                "result": event.get("result"),
            },
            to=f"room_{room_id}",
        )
        await self._broadcast_room_state(room_id)
        logger.info(f"Broadcast round {round_id} result for room {room_id}")

    async def _require_room_owner(self, sid: str, room_id: str) -> bool:
        """True when this socket is an authenticated MC that owns the room."""
        if not session_registry.is_mc(sid):
            logger.warning(f"Socket {sid} is not an authenticated MC")
            return False
        username = session_registry.mc_username(sid)
        owned = await self.room_controller.is_room_owner(room_id, username)
        if not owned:
            logger.warning(
                f"MC '{username}' does not own room {room_id}"
            )
        return owned

    async def _calculate_inline(
        self, room_id: str, round_id: int, force_calculate: bool
    ) -> dict:
        """Calculate a round inside the gateway when no worker is available"""
        try:
            result = await self.round_controller.calculate_result_use_case.execute(
                room_id, round_id, force_calculate=force_calculate
            )
        except Exception as e:
            logger.error(f"Inline calculation failed for room {room_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

        if not result.get("success"):
            logger.warning(
                f"Inline calculation rejected for room {room_id} round {round_id}: "
                f"{result.get('error')}"
            )
            return result

        await self.room_controller.end_round(room_id)
        await socket_gateway.emit_async(
            "round_result_ready",
            {
                "room_id": room_id,
                "round_id": round_id,
                "result": result.get("result"),
            },
            to=f"room_{room_id}",
        )
        await self._broadcast_room_state(room_id)
        logger.info(
            f"Broadcast round {round_id} result for room {room_id} (inline)"
        )
        return result

    async def on_round_result_failed_event(self, event: dict) -> None:
        """Handle round result failure coming back from the worker"""
        room_id = event.get("room_id")
        round_id = event.get("round_id")
        if not room_id:
            logger.error(f"Malformed round result failure event: {event}")
            return

        error = event.get("error") or "Failed to calculate result"
        logger.warning(f"Round {round_id} failed for room {room_id}: {error}")
        await socket_gateway.emit_async(
            "error",
            {"error": f"Round {round_id}: {error}", "room_id": room_id, "round_id": round_id},
            to=f"room_{room_id}",
        )

    def setup_socket_handlers(self) -> None:
        """Setup Socket.io event handlers"""

        @socket_gateway.sio.on("connect")
        async def on_connect(sid, environ, auth=None):
            """Players connect anonymously; an MC must present a valid JWT.

            The token is sent by the client in the Socket.IO handshake auth
            payload: io(url, { auth: { token } }).
            """
            token = auth.get("token") if isinstance(auth, dict) else None
            if token:
                username = verify_access_token(token)
                if not username:
                    logger.warning(f"Socket {sid} presented an invalid or expired token")
                    raise ConnectionRefusedError("invalid_token")
                session_registry.bind_mc(sid, username)

            role = "mc" if session_registry.is_mc(sid) else "player"
            logger.info(f"Client connected: {sid} (role={role})")
            await socket_gateway.emit_async(
                "connection_response", {"data": "Connected", "role": role}, to=sid
            )

        @socket_gateway.sio.on("disconnect")
        async def on_disconnect(sid):
            logger.info(f"Client disconnected: {sid}")
            session_registry.remove(sid)

        @socket_gateway.sio.on("join_room")
        async def on_join_room(sid, data):
            logger.info(f"Join room event from {sid}: {data}")
            try:
                # Room ids are case-insensitive: players type them by hand while
                # the MC gets a generated (uppercase) code.
                room_id = str(data.get("room_id") or "").strip().upper()
                if not room_id:
                    await socket_gateway.emit_async(
                        "join_room_response",
                        {"success": False, "error": "room_id is required"},
                        to=sid,
                    )
                    return

                player_name = str(data.get("player_name") or "").strip()

                # The MC role is decided by the server (JWT session), never by
                # a client-supplied flag such as data["is_mc"].
                is_mc = session_registry.is_mc(sid)

                if is_mc:
                    # The MC is not a player: it owns the room and must not
                    # appear in the player list or lose lives.
                    claim = await self.room_controller.claim_room(
                        room_id,
                        session_registry.mc_username(sid),
                        player_name or "MC",
                    )
                    if not claim.get("success"):
                        await socket_gateway.emit_async(
                            "join_room_response",
                            {"success": False, "error": claim.get("error")},
                            to=sid,
                        )
                        return

                    await socket_gateway.enter_room(sid, f"room_{room_id}")
                    state = await self._build_room_state(room_id)
                    result = {
                        "success": True,
                        "message": f"Room {room_id} ready",
                        "room_id": room_id,
                        "player": None,
                        "room_state": state,
                    }
                else:
                    result = await self.player_controller.join_room(
                        {
                            "room_id": room_id,
                            "player_name": player_name,
                            "socket_id": sid,
                            "player_id": data.get("player_id"),
                        }
                    )

                    if not result.get("success"):
                        await socket_gateway.emit_async(
                            "join_room_response", result, to=sid
                        )
                        return

                    player = result.get("player") or {}
                    player_id = player.get("player_id")

                    # Room membership is critical: without it this client receives
                    # no round_started / round_result broadcasts.
                    await socket_gateway.enter_room(sid, f"room_{room_id}")

                    # Bind this socket to the player identity so that
                    # submit_guess cannot impersonate another player.
                    session_registry.bind_player(sid, player_id, room_id)

                    # Create the player's survival lives on first join.
                    await self.score_repo.ensure_player(
                        room_id, player_id, player.get("name") or player_name
                    )

                    # Tell the room immediately. The previous broker round-trip
                    # meant the MC often missed the very first join.
                    await socket_gateway.emit_async(
                        "player_joined",
                        player,
                        to=f"room_{room_id}",
                        skip_sid=sid,
                    )
                    await self._refresh_player_count(room_id)

                    try:
                        state = await self._build_room_state(room_id)
                        result["room_state"] = state
                        result["room_id"] = room_id

                        # Late joiner: replay the current round state so the
                        # player UI does not wait for the next round.
                        if (
                            state.get("current_round", 0) > 0
                            and state.get("round_status") == RoundStatus.LOCKED
                        ):
                            await socket_gateway.emit_async(
                                "round_started",
                                {
                                    "room_id": room_id,
                                    "round_id": state["current_round"],
                                    "duration": ROUND_DURATION_SECONDS,
                                },
                                to=sid,
                            )
                            logger.info(
                                f"Replayed round {state['current_round']} to late joiner {sid}"
                            )
                    except Exception as setup_error:
                        # Side effects are best-effort: never block the join
                        # acknowledgement, but tell the client about it.
                        logger.error(
                            f"Post-join setup failed for room {room_id}: {setup_error}",
                            exc_info=True,
                        )
                        await socket_gateway.emit_async(
                            "warning",
                            {
                                "message": (
                                    f"Joined room {room_id} but some setup failed: "
                                    f"{setup_error}"
                                )
                            },
                            to=sid,
                        )

                await socket_gateway.emit_async("join_room_response", result, to=sid)
                await self._broadcast_room_state(room_id, skip_sid=sid)
            except Exception as e:
                logger.error(f"Error in join_room: {e}", exc_info=True)
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

        @socket_gateway.sio.on("submit_guess")
        async def on_submit_guess(sid, data):
            logger.info(f"Submit guess event from {sid}: {data}")
            try:
                room_id = str(data.get("room_id") or "").strip().upper()
                data = {**data, "room_id": room_id}

                # Never trust a client-supplied player_id: use the identity bound
                # to this socket when it joined the room.
                if not session_registry.is_mc(sid):
                    bound_player_id = session_registry.player_id(sid)
                    if not bound_player_id:
                        await socket_gateway.emit_async(
                            "error",
                            {"error": "Join a room before submitting a guess"},
                            to=sid,
                        )
                        return
                    data = {**data, "player_id": bound_player_id}

                    # Eliminated players are spectators for the rest of the game.
                    score = await self.score_repo.get(room_id, bound_player_id)
                    if score and score.eliminated:
                        await socket_gateway.emit_async(
                            "submit_guess_response",
                            {
                                "success": False,
                                "error": "You have been eliminated and can no longer submit guesses",
                            },
                            to=sid,
                        )
                        return

                # Validate request
                from src.modules.game_round.controller.round_controller import validate_submit_guess
                valid, error = validate_submit_guess(data)
                if not valid:
                    logger.warning(f"Invalid submit_guess: {error}")
                    await socket_gateway.emit_async("error", {"error": error}, to=sid)
                    return

                logger.info(f"Processing submit_guess for player {data.get('player_id')} in room {room_id}")
                result = await self.round_controller.submit_guess(data)
                logger.info(f"Submit guess result: {result}")

                if result.get("success"):
                    # Broadcast directly so the MC's "Waiting" badge flips
                    # immediately; no broker round-trip for UI state.
                    await socket_gateway.emit_async(
                        "player_submitted",
                        result.get("guess"),
                        to=f"room_{room_id}",
                    )
                    await self._broadcast_room_state(room_id)
                else:
                    logger.warning(f"submit_guess rejected: {result.get('error')}")

                await socket_gateway.emit_async("submit_guess_response", result, to=sid)

            except Exception as e:
                logger.error(f"Error in submit_guess: {e}", exc_info=True)
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)


        @socket_gateway.sio.on("calculate_result")
        async def on_calculate_result(sid, data):
            logger.info(f"Calculate result event from {sid}: {data}")
            try:
                # Validate request
                from src.modules.game_round.controller.round_controller import (
                    get_force_calculate,
                    validate_calculate_result,
                )
                valid, error = validate_calculate_result(data)
                if not valid:
                    await socket_gateway.emit_async("error", {"error": error}, to=sid)
                    return

                room_id = str(data.get("room_id") or "").strip().upper()
                round_id = data.get("round_id")

                # Only the MC that owns the room may end the round.
                if not await self._require_room_owner(sid, room_id):
                    await socket_gateway.emit_async(
                        "error",
                        {"error": "Only the MC that owns this room can calculate results"},
                        to=sid,
                    )
                    return

                valid, error = await self.round_controller.validate_round(
                    room_id, round_id
                )
                if not valid:
                    logger.warning(
                        f"calculate_result rejected for room {room_id} round {round_id}: {error}"
                    )
                    await socket_gateway.emit_async("error", {"error": error}, to=sid)
                    return

                force_calculate = get_force_calculate(data)

                # If no worker is consuming, run the calculation inline so the
                # round still completes instead of timing out.
                worker_status = rabbitmq_client.queue_status(QUEUE_WORKER_CALCULATE_RESULTS)
                worker_consumers = worker_status.get("consumers") or 0

                if worker_consumers == 0:
                    logger.warning(
                        f"No worker consuming {QUEUE_WORKER_CALCULATE_RESULTS}; "
                        f"calculating room {room_id} round {round_id} inline"
                    )
                    calculated = await self._calculate_inline(
                        room_id, int(round_id), force_calculate
                    )
                    if not calculated.get("success"):
                        await socket_gateway.emit_async(
                            "error",
                            {
                                "error": calculated.get("error", "Calculation failed"),
                                "room_id": room_id,
                                "round_id": int(round_id),
                            },
                            to=sid,
                        )
                        return

                    await socket_gateway.emit_async(
                        "calculate_result_response",
                        {
                            "success": True,
                            "status": "completed",
                            "message": "Calculation completed inline (no worker available)",
                            "room_id": room_id,
                            "round_id": int(round_id),
                        },
                        to=sid,
                    )
                    return

                # Hand the calculation to the worker
                published = message_publisher.publish_calculate_result(
                    {
                        "room_id": room_id,
                        "round_id": int(round_id),
                        "force_calculate": force_calculate,
                    }
                )

                if not published:
                    await socket_gateway.emit_async(
                        "error",
                        {"error": "Message broker unavailable, cannot calculate result"},
                        to=sid,
                    )
                    return

                await socket_gateway.emit_async(
                    "calculate_result_response",
                    {
                        "success": True,
                        "status": "queued",
                        "message": "Calculation queued",
                        "room_id": room_id,
                        "round_id": int(round_id),
                    },
                    to=sid,
                )
            except Exception as e:
                logger.error(f"Error in calculate_result: {e}")
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

        @socket_gateway.sio.on("start_round")
        async def on_start_round(sid, data):
            logger.info(f"Start round event from {sid}: {data}")
            try:
                room_id = str(data.get("room_id") or "").strip().upper()
                if not room_id:
                    await socket_gateway.emit_async(
                        "error", {"error": "room_id is required"}, to=sid
                    )
                    return

                # Only the MC that owns the room may start a round.
                if not await self._require_room_owner(sid, room_id):
                    await socket_gateway.emit_async(
                        "error",
                        {"error": "Only the MC that owns this room can start a round"},
                        to=sid,
                    )
                    return

                state = await self._build_room_state(room_id)
                alive_players = [
                    player for player in state.get("players", [])
                    if not player.get("eliminated")
                ]
                if not alive_players:
                    await socket_gateway.emit_async(
                        "error",
                        {"error": "No players are still alive in this room"},
                        to=sid,
                    )
                    return

                round_id = await self.room_controller.start_round(room_id)
                logger.info(f"Room {room_id} started round {round_id}")

                # Broadcast round_started to all players in room
                try:
                    await socket_gateway.emit_to_room(
                        "round_started",
                        {
                            "room_id": room_id,
                            "round_id": round_id,
                            "duration": ROUND_DURATION_SECONDS,
                        },
                        room=f"room_{room_id}",
                        skip_sid=sid,
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast round_started: {e}")

                # Confirm to MC
                await socket_gateway.emit_async(
                    "start_round_response",
                    {
                        "success": True,
                        "message": "Round started",
                        "room_id": room_id,
                        "round_id": round_id,
                        "duration": ROUND_DURATION_SECONDS,
                    },
                    to=sid,
                )

                # New round => every "submitted" badge resets.
                await self._broadcast_room_state(room_id)
            except Exception as e:
                logger.error(f"Error in start_round: {e}")
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

        @socket_gateway.sio.on("request_room_state")
        async def on_request_room_state(sid, data=None):
            """Allow clients to resync after a reconnect or a page refresh."""
            try:
                room_id = str((data or {}).get("room_id") or "").strip().upper()
                if not room_id:
                    return

                if not session_registry.is_mc(sid):
                    session = session_registry.get(sid) or {}
                    if session.get("room_id") != room_id:
                        await socket_gateway.emit_async(
                            "error",
                            {"error": "Join the room before requesting its state"},
                            to=sid,
                        )
                        return

                state = await self._build_room_state(room_id)
                await socket_gateway.emit_async("room_state", state, to=sid)
            except Exception as e:
                logger.error(f"Error in request_room_state: {e}")
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

        @socket_gateway.sio.on("list_rooms")
        async def on_list_rooms(sid, data):
            logger.info(f"List rooms request from {sid}")
            try:
                if not session_registry.is_mc(sid):
                    await socket_gateway.emit_async(
                        "error",
                        {"error": "Only the MC can list rooms"},
                        to=sid,
                    )
                    return

                # An MC only ever sees the rooms it owns.
                rooms = await self.room_controller.list_rooms_for_mc(
                    session_registry.mc_username(sid)
                )
                await socket_gateway.emit_async(
                    "rooms_list",
                    {"success": True, "rooms": rooms},
                    to=sid,
                )
            except Exception as e:
                logger.error(f"Error in list_rooms: {e}")
                await socket_gateway.emit_async("error", {"error": str(e)}, to=sid)

    async def shutdown(self) -> None:
        """Shutdown handler"""
        logger.info("Application shutting down...")
        if self.event_consumer:
            self.event_consumer.stop()
        rabbitmq_client.disconnect()
        await redis_client.disconnect()


# Global app instance
app_instance = GameApplication()


# HTTP endpoints
async def health(request):
    """Health check endpoint"""
    worker_queue = rabbitmq_client.queue_status(QUEUE_WORKER_CALCULATE_RESULTS)
    worker_consumers = worker_queue.get("consumers") or 0
    return JSONResponse(
        {
            "status": "ok",
            "broker": "connected" if rabbitmq_client.consumer_alive else "disconnected",
            "worker": {
                "queue": worker_queue.get("queue"),
                "consumers": worker_queue.get("consumers"),
                "pending_messages": worker_queue.get("messages"),
                "alive": worker_consumers > 0,
                "error": worker_queue.get("error"),
            },
        }
    )


@asynccontextmanager
async def lifespan(app):
    await app_instance.initialize()
    try:
        yield
    finally:
        await app_instance.shutdown()


async def login(request: Request):
    """Exchange MC credentials for a JWT access token."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON body"}, status_code=400
        )

    username = body.get("username") or ""
    password = body.get("password") or ""
    token = auth_service.authenticate(username, password)
    if not token:
        return JSONResponse(
            {"success": False, "error": "Invalid username or password"},
            status_code=401,
        )

    return JSONResponse(
        {
            "success": True,
            "token": token,
            "token_type": "bearer",
            "expires_in": settings.JWT_EXPIRE_MINUTES * 60,
        }
    )


# Starlette app
starlette_app = Starlette(
    debug=settings.DEBUG,
    routes=[
        Route("/health", health),
        Route("/auth/login", login, methods=["POST"]),
    ],
    lifespan=lifespan,
)

# CORS middleware
starlette_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Socket.IO handles polling and WebSocket traffic; Starlette handles other routes.
app = ASGIApp(socket_gateway.sio, other_asgi_app=starlette_app)


if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    host = "0.0.0.0"
    port = int(os.getenv("PORT", settings.SOCKET_IO_PORT))
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("src.app:app", host=host, port=port, log_level="info", reload=False)
