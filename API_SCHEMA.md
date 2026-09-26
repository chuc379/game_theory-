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
  "socket_id": "socket_id_generated_by_socket.io"
}
```

- **Response** (`join_room_response`):
```json
{
  "success": true,
  "message": "Player Nguyễn Văn A joined successfully",
  "player": {
    "player_id": "usr_abc123",
    "socket_id": "socket_12345",
    "name": "Nguyễn Văn A",
    "is_online": true,
    "joined_at": 1727337000000
  }
}
```

#### `player_joined` (Broadcast)
- **Direction**: Server → All Clients (except sender)
- **Payload**: Player object (same as join_room_response.player)

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
    "total_players": 30,
    "average": 45.5,
    "target": 30.33,
    "winner": {
      "player_id": "usr_xyz789",
      "player_name": "Trần Thị B",
      "guess_number": 30.0,
      "difference": 0.33
    },
    "calculated_at": 1727337090000
  }
}
```

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
  console.log('Winner:', data.result.winner.player_name);
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
