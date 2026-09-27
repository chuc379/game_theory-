"""
Swagger/OpenAPI documentation for Socket.io API
"""

SWAGGER_SPEC = {
    "swagger": "2.0",
    "info": {
        "title": "Game Theory - Guess 2/3 of Average API",
        "version": "1.0.0",
        "description": "Real-time multiplayer game API",
        "contact": {"name": "Game Theory Team"},
    },
    "host": "game-theory-gateway.onrender.com",
    "basePath": "/",
    "schemes": ["https", "http"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "paths": {
        "/health": {
            "get": {
                "tags": ["Health"],
                "summary": "Health check",
                "operationId": "healthCheck",
                "responses": {
                    "200": {
                        "description": "Server is healthy",
                        "schema": {
                            "type": "object",
                            "properties": {"status": {"type": "string"}},
                        },
                    }
                },
            }
        },
        "/socket.io": {
            "get": {
                "tags": ["Socket.io"],
                "summary": "WebSocket connection endpoint",
                "description": "Connect to Socket.io for real-time events",
                "responses": {
                    "200": {"description": "Socket.io protocol response"}
                },
            }
        },
    },
    "definitions": {
        "PlayerSession": {
            "type": "object",
            "properties": {
                "player_id": {"type": "string", "description": "Unique player ID"},
                "socket_id": {"type": "string", "description": "Socket connection ID"},
                "name": {"type": "string", "description": "Player name"},
                "is_online": {"type": "boolean", "description": "Online status"},
                "joined_at": {"type": "number", "description": "Join timestamp"},
            },
        },
        "PlayerGuess": {
            "type": "object",
            "properties": {
                "player_id": {"type": "string"},
                "player_name": {"type": "string"},
                "guess_number": {"type": "number", "minimum": 0, "maximum": 100},
                "submitted_at": {"type": "number"},
            },
        },
        "Winner": {
            "type": "object",
            "properties": {
                "player_id": {"type": "string"},
                "player_name": {"type": "string"},
                "guess_number": {"type": "number"},
                "difference": {"type": "number"},
            },
        },
        "RoundResult": {
            "type": "object",
            "properties": {
                "total_players": {"type": "integer"},
                "average": {"type": "number"},
                "target": {"type": "number"},
                "winner": {"$ref": "#/definitions/Winner"},
                "calculated_at": {"type": "number"},
            },
        },
        "RoomInfo": {
            "type": "object",
            "properties": {
                "room_id": {"type": "string"},
                "current_round": {"type": "integer"},
                "status": {"type": "string", "enum": ["ACTIVE", "CLOSED"]},
            },
        },
    },
    "x-socket-io-events": {
        "connect": {
            "description": "Client connects to server",
            "payload": {},
            "response": {
                "type": "object",
                "properties": {"data": {"type": "string"}},
            },
        },
        "join_room": {
            "description": "Player joins a game room",
            "payload": {
                "type": "object",
                "required": ["room_id", "player_name"],
                "properties": {
                    "room_id": {"type": "string", "example": "CLB30"},
                    "player_name": {"type": "string", "example": "Nguyễn Văn A"},
                },
            },
            "response": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "player": {"$ref": "#/definitions/PlayerSession"},
                },
            },
        },
        "submit_guess": {
            "description": "Player submits their guess",
            "payload": {
                "type": "object",
                "required": ["room_id", "round_id", "player_id", "player_name", "guess_number"],
                "properties": {
                    "room_id": {"type": "string"},
                    "round_id": {"type": "integer"},
                    "player_id": {"type": "string"},
                    "player_name": {"type": "string"},
                    "guess_number": {"type": "number", "minimum": 0, "maximum": 100},
                },
            },
            "response": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "guess": {"$ref": "#/definitions/PlayerGuess"},
                },
            },
        },
        "calculate_result": {
            "description": "Calculate round results",
            "payload": {
                "type": "object",
                "required": ["room_id", "round_id"],
                "properties": {
                    "room_id": {"type": "string"},
                    "round_id": {"type": "integer"},
                },
            },
            "response": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                },
            },
        },
        "player_joined": {
            "description": "Broadcast when player joins (sent to all except sender)",
            "payload": {"$ref": "#/definitions/PlayerSession"},
        },
        "player_submitted": {
            "description": "Broadcast when player submits guess",
            "payload": {"$ref": "#/definitions/PlayerGuess"},
        },
        "round_result_ready": {
            "description": "Broadcast when round results are ready",
            "payload": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "round_id": {"type": "integer"},
                    "result": {"$ref": "#/definitions/RoundResult"},
                },
            },
        },
        "error": {
            "description": "Error event",
            "payload": {
                "type": "object",
                "properties": {"error": {"type": "string"}},
            },
        },
    },
}
