# Game Theory API Schema

## Socket.io Events Documentation

### Connection & Room Management

#### `connect`
- **Direction**: Server → Client
- **Payload**: 
```json
{
  "data": "Connected"
}
```

#### `join_room`
- **Direction**: Client → Server
- **Payload**:
```json
{
  "room_id": "CLB30",
  "player_name": "Nguyễn Văn A",
  "player_id": "usr_abc123"
}
```
- `room_id` is normalized to uppercase, so `clb30` and `CLB30` join the same room.
- `player_id` is optional and lets a reconnecting client keep its identity.
- The MC is decided by the server (JWT session), not by a client flag.

- **Response** (`join_room_response`):
```json
{
  "success": true,
  "message": "Player Nguyễn Văn A joined successfully",
  "room_id": "CLB30",
  "player": {
    "player_id": "usr_abc123",
    "socket_id": "socket_12345",
    "name": "Nguyễn Văn A",
    "is_online": true,
    "joined_at": 1727337000000
  },
  "room_state": { "room_id": "CLB30", "players": [], "scoreboard": [] }
}
```

#### `player_joined` (Broadcast)
- **Direction**: Server → All Clients (except sender)
- **Payload**: Player object (same as join_room_response.player)
- Emitted directly by the gateway, so the first join is never lost.

#### `room_state` (Broadcast / Response)
- **Direction**: Server → All Clients in the room
- **Payload**: authoritative snapshot, sent after join, submit, round start and
  round result, as well as in response to `request_room_state`:
```json
{
  "room_id": "CLB30",
  "current_round": 2,
  "round_status": "LOCKED",
  "started_lives": 10,
  "players": [
    {
      "player_id": "usr_abc123",
      "player_name": "Nguyễn Văn A",
      "socket_id": "socket_12345",
      "is_online": true,
      "submitted": true,
      "points": 8,
      "eliminated": false,
      "rounds_played": 2,
      "wins": 0,
      "last_delta": -1
    }
  ],
  "scoreboard": [
    {
      "player_id": "usr_abc123",
      "player_name": "Nguyễn Văn A",
      "points": 8,
      "total_points": 8,
      "eliminated": false,
      "last_delta": -1,
      "rank": 1
    }
  ]
}
```
- `round_status`: `WAITING` | `LOCKED` | `ENDED`.

#### `request_room_state`
- **Direction**: Client → Server
- **Payload**:
```json
{ "room_id": "CLB30" }
```
- The server replies with a personal `room_state`. Only sockets that already
  joined the room may request it. Used after a reconnect or page refresh.

### Game Round

#### `submit_guess`
- **Direction**: Client → Server
- **Payload**:
```json
{
  "room_id": "CLB30",
  "round_id": 1,
  "player_id": "usr_abc123",
  "player_name": "Nguyễn Văn A",
  "guess_number": 22.5
}
```

- **Response** (`submit_guess_response`):
```json
{
  "success": true,
  "message": "Guess submitted successfully",
  "guess": {
    "player_id": "usr_abc123",
    "player_name": "Nguyễn Văn A",
    "guess_number": 22.5,
    "submitted_at": 1727337039000
  }
}
```

#### `player_submitted` (Broadcast)
- **Direction**: Server → All Clients
- **Payload**: Guess object (same as submit_guess_response.guess)

#### `calculate_result`
- **Direction**: Client → Server
- **Payload**:
```json
{
  "room_id": "CLB30",
  "round_id": 1
}
```

- **Response** (`calculate_result_response`):
```json
{
  "success": true,
  "message": "Calculating result..."
}
```

#### `round_result_ready` (Broadcast)
- **Direction**: Server → All Clients (after calculation)
- **Payload**:
```json
{
  "room_id": "CLB30",
  "round_id": 1,
  "result": {
    "total_players": 5,
    "average": 45.5,
    "target": 30.33,
    "winner": {
      "player_id": "usr_xyz789",
      "player_name": "Trần Thị B",
      "guess_number": 30.0,
      "difference": 0.33
    },
    "rule": "survival",
    "convergence": false,
    "guesses": [
      {
        "player_id": "usr_abc123",
        "player_name": "Nguyễn Văn A",
        "guess_number": 60.0,
        "submitted_at": 1727337039000
      }
    ],
    "losers": ["usr_abc123"],
    "correct": ["usr_xyz789"],
    "eliminated": [
      {
        "player_id": "usr_abc123",
        "player_name": "Nguyễn Văn A",
        "points": 0,
        "eliminated": true,
        "last_delta": -1
      }
    ],
    "game_over": false,
    "survivor": null,
    "scoreboard": [
      {
        "player_id": "usr_xyz789",
        "player_name": "Trần Thị B",
        "points": 3,
        "eliminated": false,
        "last_delta": 0,
        "rank": 1
      }
    ],
    "calculated_at": 1727337090000
  }
}
```
- `winner` may be `null` (converged round or nobody submitted).
- `eliminated` contains only players eliminated by **this** round.
- `game_over` is true when at most 1 player is still alive.

### Survival Scoring Rules

- Every player starts with `STARTING_LIVES = 10`.
- Normal round: everyone whose guess is not the winning guess loses 1 life.
  Players that did not submit count as wrong.
- Converged round (`target <= 0.01`): every player who picked `0` loses 1 life;
  everyone else is safe.
- Lives are clamped at 0. Reaching 0 sets `eliminated = true`; eliminated
  players cannot submit guesses (`submit_guess_response.success = false`).
- Scores are stored in Redis and broadcast through `room_state`; clients must
  not compute lives locally.

### Error Handling

#### `error` (Broadcast)
- **Direction**: Server → Client (on error)
- **Payload**:
```json
{
  "error": "Error message describing what went wrong"
}
```

## Redis Data Structure (Backend Reference)

### Keys Pattern
- `room:{room_id}:info` → Room metadata
- `room:{room_id}:players` → Hash of all players
- `room:{room_id}:round:{round_id}:guesses` → Hash of guesses
- `room:{room_id}:round:{round_id}:result` → Round result
- `room:{room_id}:scores` → Hash of survival scores (lives, eliminations)
- `room:{room_id}:history` → List of past results

## Data Validation Rules

### Player Name
- Min length: 1 character
- Max length: 100 characters
- Required

### Guess Number
- Min: 0
- Max: 100
- Type: Float (decimal allowed)
- Required

### Room ID
- Type: String
- Format: Alphanumeric (e.g., "CLB30")
- Required

## Integration Guide for Frontend

1. **Connect to Socket.io**
```javascript
const socket = io('https://<your-domain>:5000');
```

2. **Join Room**
```javascript
socket.emit('join_room', {
  room_id: 'CLB30',
  player_name: 'Nguyễn Văn A'
});

socket.on('join_room_response', (data) => {
  if (data.success) {
    console.log('Joined room:', data.player);
  }
});
```

3. **Listen for Players Joining**
```javascript
socket.on('player_joined', (player) => {
  console.log('Player joined:', player.name);
});
```

4. **Submit Guess**
```javascript
socket.emit('submit_guess', {
  room_id: 'CLB30',
  round_id: 1,
  player_id: player_data.player_id,
  player_name: player_data.name,
  guess_number: 22.5
});

socket.on('submit_guess_response', (data) => {
  if (data.success) {
    console.log('Guess submitted:', data.guess);
  }
});
```

5. **Listen for Other Submissions**
```javascript
socket.on('player_submitted', (guess) => {
  console.log(`${guess.player_name} submitted: ${guess.guess_number}`);
});
```

6. **Wait for Results**
```javascript
socket.on('round_result_ready', (data) => {
  console.log('Round result:', data.result);
  // winner is null on a converged round (or when nobody submitted)
  console.log('Winner:', data.result.winner?.player_name ?? '—');
});
```

## Event Flow Diagram

```
Client                 Socket Gateway          Message Broker       Worker
  │                          │                       │                │
  ├─ join_room ────────────→ │                       │                │
  │                          ├─ save to Redis        │                │
  │ ←─ join_room_response ──┤                       │                │
  │                          ├─ broadcast ────→ All clients           │
  │                          │                       │                │
  ├─ submit_guess ────────→ │                       │                │
  │                          ├─ save to Redis        │                │
  │ ←─ submit_guess_response─┤                       │                │
  │                          ├─ broadcast ────→ All clients           │
  │                          │                       │                │
  ├─ calculate_result ──→ │                       │                │
  │                          ├─ publish event ──→ RabbitMQ           │
  │                          │                       ├─ consume ────→ │
  │ ←─ calculate_result_response                    │                │
  │                          │                       │                │
  │                          │                       │    ← get all guesses
  │                          │    ← publish result ──┤                │
  │                          │                       │                │
  │ ← round_result_ready ─────────────────────────────                │
  │                                                                    │
```

## Deployment Notes

- Socket.io runs on port 5000
- Worker runs on separate process (port 5001)
- Redis stores all session/game data
- RabbitMQ coordinates async tasks
- All communication is real-time via WebSocket
