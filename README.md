# Game Theory - Guess 2/3 of Average

Real-time multiplayer game backend built with Python, Socket.io, Redis, and RabbitMQ.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Zalo Webview)             │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────────────────────────────────────────┐
    │        Socket.io Gateway Server             │
    │  - Player connection management             │
    │  - Real-time event broadcasting             │
    │  - API request validation                   │
    └─────────────────┬───────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
    ┌────────────┐            ┌────────────┐
    │   Redis    │            │ RabbitMQ   │
    │   Cache    │            │   Broker   │
    │(Session &  │            │ (Async     │
    │ Game Data) │            │  Queue)    │
    └────────────┘            └────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   Game Worker       │
                    │ - Calc averages     │
                    │ - Determine winners │
                    │ - Store results     │
                    └─────────────────────┘
```

## Project Structure

### Clean Architecture Per Module

```
src/
├── shared/                    # Shared infrastructure
│   ├── domain/               # Domain models & interfaces
│   ├── infrastructure/       # Redis, RabbitMQ, Socket.io adapters
│   └── constants.py
│
├── modules/
│   ├── player/              # Player Module
│   │   ├── domain/
│   │   ├── adapter/
│   │   ├── use_cases/
│   │   └── controller/      # API schema
│   │
│   ├── game_round/          # Game Round Module
│   │   ├── domain/
│   │   ├── adapter/
│   │   ├── use_cases/
│   │   └── controller/      # API schema
│   │
│   ├── room/                # Room Module
│   │   ├── domain/
│   │   ├── adapter/
│   │   └── controller/      # API schema
│   │
│   └── event_listener/      # Observer pattern
│
├── worker/                  # Async worker
└── app.py                   # Main entry point
```

### Design Patterns Used

- **Clean Architecture**: Separation of concerns across domain, use cases, adapters
- **Factory Pattern**: `PlayerFactory`, `RoundFactory` for entity creation
- **Repository Pattern**: Interface-based data access abstraction
- **Observer Pattern**: Event listeners for state changes
- **Adapter Pattern**: Infrastructure adapters (Redis, RabbitMQ, Socket.io)
- **Dependency Injection**: Constructor-based DI for loose coupling

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Or manual setup: Redis + RabbitMQ

### Quick Start with Docker

1. **Clone and setup**
```bash
cd BE
cp .env.example .env
```

2. **Start all services**
```bash
docker-compose up -d
```

Services will be available at:
- Socket.io Gateway: `http://localhost:5000`
- RabbitMQ Admin: `http://localhost:15672` (guest/guest)
- Redis: `localhost:6379`

### Local Development Setup

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Start Redis**
```bash
redis-server
```

3. **Start RabbitMQ** (or Docker)
```bash
docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3.12-management-alpine
```

4. **Setup environment**
```bash
cp .env.example .env
```

5. **Run Gateway Server**
```bash
python -m src.app
```

6. **Run Worker** (in another terminal)
```bash
python -m src.worker.game_worker
```

## API Documentation

See `API_SCHEMA.md` for complete Socket.io event documentation.

### Key Events

- `join_room` - Player joins game
- `submit_guess` - Player submits their guess
- `calculate_result` - MC triggers result calculation
- `round_result_ready` - Broadcast final results to all players

## Configuration

Edit `.env` to configure:

```
REDIS_HOST=localhost
REDIS_PORT=6379

RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

SOCKET_IO_PORT=5000
WORKER_PORT=5001

ENV=development
DEBUG=true
```

## Module Breakdown

### Player Module
- Join room handling
- Player session management
- Player validation

**Key Files**:
- `player_entity.py` - Domain model
- `player_repository.py` - Data access interface
- `player_cache_repository.py` - Redis implementation
- `join_room.py` - Use case logic
- `player_factory.py` - Entity factory
- `player_controller.py` - API schema

### Game Round Module
- Guess submission
- Result calculation
- Winner determination

**Key Files**:
- `round_entity.py` - Domain model with calculation logic
- `round_cache_repository.py` - Redis adapter for guesses & results
- `submit_guess.py` - Use case for guess submission
- `calculate_result.py` - Use case for calculation
- `round_controller.py` - API schema with Pydantic models

### Room Module
- Room creation
- Round management
- History tracking

**Key Files**:
- `room_entity.py` - Domain model
- `room_cache_repository.py` - Redis adapter
- `room_controller.py` - API schema

### Worker
- Async task processing from RabbitMQ
- Result calculations
- Event publishing

**Key Files**:
- `game_worker.py` - Worker entry point
- `task_handlers.py` - Task handlers

## Data Flow

### Player Submission Flow
1. Client emits `submit_guess` event
2. Gateway validates request via `SubmitGuessRequest` schema
3. `SubmitGuessUseCase` saves guess to Redis
4. Event published to all clients via `player_submitted`
5. Message published to RabbitMQ for audit trail

### Result Calculation Flow
1. MC emits `calculate_result` event
2. Gateway publishes to RabbitMQ
3. Worker consumes message
4. Worker fetches all guesses from Redis
5. `CalculateResultUseCase` calculates average & target
6. Winner determined and result saved to Redis
7. `round_result_ready` event broadcasted to all clients

## Deployment

### Docker Compose
```bash
docker-compose up -d
```

### Cloud Deployment (e.g., AWS/Azure)
1. Push to container registry
2. Deploy services with orchestration (ECS, AKS, etc.)
3. Use managed services for Redis & RabbitMQ
4. Configure environment variables per environment

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests (TODO: add test suite)
pytest tests/
```

## Performance Considerations

- **WebSocket**: < 50ms latency for real-time updates
- **Redis**: In-memory caching for instant data access
- **RabbitMQ**: Async task queue prevents blocking
- **Worker**: Separate process for heavy calculations
- **Scaling**: Stateless gateway allows horizontal scaling

## Security Considerations

- Socket.io CORS configured
- Input validation via Pydantic schemas
- No sensitive data in Redis/logs
- RabbitMQ uses credentials (change default password in production)

## Future Enhancements

- Authentication/Authorization
- Persistent logging
- Game statistics & analytics
- Leaderboard persistence
- Multiple concurrent rooms
- Admin dashboard
- API rate limiting

## License

[Add your license here]

## Support

For issues or questions, contact the development team.
