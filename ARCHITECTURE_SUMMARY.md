# Architecture Summary - Game Theory Backend

## Design Principles Applied

### 1. Clean Architecture
- **Domain Layer**: Pure business logic, no external dependencies
  - `entities.py` - Core business objects (PlayerSession, PlayerGuess, RoundResult)
  - `repositories.py` - Interfaces defining data access contracts
  - `events.py` - Domain events for state changes

- **Use Cases Layer**: Business orchestration
  - `join_room.py` - Player joining logic
  - `submit_guess.py` - Guess submission logic
  - `calculate_result.py` - Result calculation logic

- **Adapter Layer**: External service integration
  - `player_cache_repository.py` - Redis implementation
  - `round_cache_repository.py` - Redis implementation
  - `socket_gateway.py` - Socket.io wrapper

- **Controller Layer**: API schema & validation
  - `player_controller.py` - Pydantic models for player APIs
  - `round_controller.py` - Pydantic models for round APIs
  - `room_controller.py` - Pydantic models for room APIs

### 2. Modular Architecture
Each module is self-contained with its own:
- Domain models
- Data access repositories
- Business logic (use cases)
- API schema (controllers)

**Modules:**
- `player/` - Player management
- `game_round/` - Game round & guess logic
- `room/` - Room management
- `event_listener/` - Event handling

### 3. Design Patterns

#### Factory Pattern
```python
# player/use_cases/player_factory.py
player = PlayerFactory.create_player("Nguyễn Văn A", socket_id)

# game_round/use_cases/round_factory.py
round = RoundFactory.create_round(1)
```
**Why**: Centralizes entity creation logic, ensures consistency

#### Repository Pattern
```python
# player/domain/player_repository.py (Interface)
class IPlayerRepository(ABC):
    async def save(self, room_id: str, player: PlayerEntity) -> None:
        pass

# player/adapter/player_cache_repository.py (Implementation)
class PlayerCacheRepository(IPlayerRepository):
    async def save(self, room_id: str, player: PlayerEntity) -> None:
        # Redis implementation
```
**Why**: Decouples domain logic from data access, easy to swap implementations

#### Observer Pattern (Events)
```python
# Domain events trigger listeners
@dataclass
class PlayerSubmitGuessEvent(DomainEvent):
    event_type: str = "PLAYER_SUBMIT_GUESS"
    
# event_listener/round_event_listener.py listens and reacts
```
**Why**: Loose coupling between modules, easy to add new behaviors

#### Adapter Pattern
```python
# shared/infrastructure/socket_io/socket_gateway.py
class SocketGateway:
    def emit_async(self, event: str, data: dict) -> None:
        # Wraps Socket.io for easier use

# Hides complex Socket.io internals
```
**Why**: Abstracts external library details, single responsibility

### 4. Async/Non-blocking with RabbitMQ

```
Client Submit              
    ↓                     
Validate & Save to Redis  (Fast)
    ↓                     
Publish to RabbitMQ       (Returns immediately)
    ↓                     
Socket Gateway responds    (No blocking)
    ↓                     
Worker consumes from queue (Async processing)
    ↓                     
Calculate result
    ↓                     
Broadcast via Socket.io   (Real-time)
```

**Why**: Prevents blocking, scales to 100+ concurrent users

### 5. Data Storage Strategy

All data in Redis (no database):
- **Hash**: Player sessions, guesses
- **String**: Room info, results
- **List**: History

**Keys Pattern**:
```
room:CLB30:info → Room metadata
room:CLB30:players → {playerId: PlayerData}
room:CLB30:round:1:guesses → {playerId: GuessData}
room:CLB30:round:1:result → ResultJSON
room:CLB30:history → [Result1, Result2, ...]
```

**Why**: 
- Lightning fast access
- TTL support for auto-cleanup
- No database latency
- Perfect for session/cache data

## Code Organization

### Dependency Flow (Clean)
```
Controller (API Schema)
    ↓
Use Cases (Business Logic)
    ↓
Domain Entities (Business Objects)
    ↓
Repository Interface (Abstraction)
    ↓
Adapter (Redis, RabbitMQ)
```

**Each layer**:
- Only knows about layers below
- Can be tested independently
- Can be swapped/extended

### Example: Join Room Use Case

```
1. Controller receives request
   ↓
2. JoinRoomUseCase.execute()
   ↓
3. PlayerFactory.create_player()
   ↓
4. PlayerEntity.is_valid()
   ↓
5. player_repository.save()  (Interface)
   ↓
6. PlayerCacheRepository.save()  (Redis)
   ↓
7. Emit event via Socket.io
```

## API Contract (Pydantic Schemas)

Frontend ONLY needs to read schemas in controllers:

```python
# Round controller has all schemas
class SubmitGuessRequest(BaseModel):
    room_id: str
    round_id: int
    guess_number: float

class RoundResultSchema(BaseModel):
    total_players: int
    average: float
    target: float
    winner: WinnerSchema

# Frontend knows exactly what to send/expect
```

**Why**: 
- Frontend doesn't need to read business logic
- Clear contract between FE & BE
- Pydantic validation ensures correctness
- Auto-generated docs

## Event Flow Diagram

```
┌────────────────────────────────────────────────────────────┐
│ Player joins → Saved to Redis                              │
│ (Fast, synchronous)                                        │
└────────────────────────────────────────────────────────────┘
        ↓
┌────────────────────────────────────────────────────────────┐
│ Player submits guess                                        │
│ 1. Save to Redis (immediate)                               │
│ 2. Return response (non-blocking)                           │
│ 3. Publish to RabbitMQ                                      │
└────────────────────────────────────────────────────────────┘
        ↓
┌────────────────────────────────────────────────────────────┐
│ MC clicks "Calculate"                                       │
│ 1. Publish CALCULATE event to RabbitMQ                      │
│ 2. Return immediately                                       │
└────────────────────────────────────────────────────────────┘
        ↓
┌────────────────────────────────────────────────────────────┐
│ Worker processes (async)                                   │
│ 1. Get all guesses from Redis                               │
│ 2. Calculate average = Sum(guesses) / count                │
│ 3. Calculate target = average * 2/3                         │
│ 4. Find winner = min(|guess - target|)                      │
│ 5. Save result to Redis                                     │
│ 6. Publish RESULT_READY event                               │
└────────────────────────────────────────────────────────────┘
        ↓
┌────────────────────────────────────────────────────────────┐
│ Socket Gateway receives event                              │
│ Broadcasts ROUND_RESULT_READY to all clients               │
└────────────────────────────────────────────────────────────┘
```

## Key Abstractions for Non-Techs

When building frontend, you ONLY need:

### 1. Understand Data Shapes
```python
# From controller schemas - that's it!
Player {
  player_id: string
  name: string
  joined_at: timestamp
}

Guess {
  player_id: string
  guess_number: float (0-100)
  submitted_at: timestamp
}

Result {
  average: float
  target: float
  winner: {name, guess_number, difference}
}
```

### 2. Understand Events
```javascript
// Emit (send to backend)
socket.emit('join_room', {...})
socket.emit('submit_guess', {...})
socket.emit('calculate_result', {...})

// Listen (receive from backend)
socket.on('join_room_response', handler)
socket.on('player_submitted', handler)
socket.on('round_result_ready', handler)
```

### 3. No need to understand:
- Redis internals
- RabbitMQ architecture
- Repository patterns
- Factory patterns
- Clean architecture

Frontend simply calls the right events and handles responses!

## Module Interface (What FE needs to know)

```python
# That's literally all FE reads from BE:

# From player_controller.py
class JoinRoomRequest:
  room_id: str
  player_name: str

class PlayerSessionSchema:
  player_id: str
  name: str
  is_online: bool

# From round_controller.py  
class SubmitGuessRequest:
  room_id: str
  round_id: int
  guess_number: float (0-100)

class RoundResultSchema:
  average: float
  target: float
  winner: WinnerSchema
```

## Scaling Considerations

**Current Design supports:**
- 30-100 concurrent users (easily)
- Real-time < 50ms latency
- Multiple rooms independently
- Horizontal scaling of Gateway (stateless)

**To scale further:**
- Add Redis Cluster (for persistence)
- Add load balancer (multiple Gateway instances)
- Multiple Workers (RabbitMQ distributes tasks)
- Upgrade to managed services (AWS ElastiCache, RabbitMQ service)

## Next Steps for Frontend

1. Read `API_SCHEMA.md` for all Socket.io events
2. Read controller schemas in `player_controller.py`, `round_controller.py`
3. Connect to `http://localhost:5000` with Socket.io client
4. Implement UI based on events

That's it! Clean separation means FE stays simple.
