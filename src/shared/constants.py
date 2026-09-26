"""
Constants for Redis keys and RabbitMQ routing keys
"""

# Redis Key Patterns
REDIS_ROOM_INFO = "room:{room_id}:info"
REDIS_ROOM_PLAYERS = "room:{room_id}:players"
REDIS_ROUND_GUESSES = "room:{room_id}:round:{round_id}:guesses"
REDIS_ROUND_RESULT = "room:{room_id}:round:{round_id}:result"
REDIS_ROOM_HISTORY = "room:{room_id}:history"

# RabbitMQ
RABBITMQ_EXCHANGE = "game.events.exchange"
RABBITMQ_EXCHANGE_TYPE = "topic"

ROUTING_KEY_PLAYER_SUBMIT = "game.player.submit"
ROUTING_KEY_CALCULATE_RESULT = "game.round.calculate"

QUEUE_PLAYER_GUESSES = "player.guesses.queue"
QUEUE_CALCULATE_RESULTS = "calculate.results.queue"

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
