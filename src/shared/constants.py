"""
Constants for Redis keys and RabbitMQ routing keys
"""

# Redis Key Patterns
REDIS_ROOM_INFO = "room:{room_id}:info"
REDIS_ROOM_PLAYERS = "room:{room_id}:players"
REDIS_ROUND_GUESSES = "room:{room_id}:round:{round_id}:guesses"
REDIS_ROUND_RESULT = "room:{room_id}:round:{round_id}:result"
REDIS_ROOM_HISTORY = "room:{room_id}:history"
REDIS_ROOM_CURRENT_ROUND = "room:{room_id}:current_round"
REDIS_ROOM_ROUND_STATUS = "room:{room_id}:round_status"

ROUND_DURATION_SECONDS = 30

# RabbitMQ
RABBITMQ_EXCHANGE = "game.events.exchange"
RABBITMQ_EXCHANGE_TYPE = "topic"
RABBITMQ_PREFETCH_COUNT = 10

ROUTING_KEY_PLAYER_JOINED = "game.player.joined"
ROUTING_KEY_PLAYER_SUBMIT = "game.player.submit"
ROUTING_KEY_ROUND_CALCULATE = "game.round.calculate"
ROUTING_KEY_ROUND_RESULT_READY = "game.round.result.ready"
ROUTING_KEY_ROUND_RESULT_FAILED = "game.round.result.failed"

QUEUE_GATEWAY_PLAYER_EVENTS = "gateway.player.events.queue"
QUEUE_GATEWAY_ROUND_RESULTS = "gateway.round.results.queue"
QUEUE_WORKER_CALCULATE_RESULTS = "worker.calculate.results.queue"

# Round Status
class RoundStatus:
    WAITING = "WAITING"
    LOCKED = "LOCKED"
    ENDED = "ENDED"

# Socket Events
class SocketEvents:
    PLAYER_SUBMITTED = "PLAYER_SUBMITTED"
    ROUND_RESULT_READY = "ROUND_RESULT_READY"
    PLAYER_JOINED = "PLAYER_JOINED"
    PLAYER_LEFT = "PLAYER_LEFT"
