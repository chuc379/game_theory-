# Backend Testing Guide

## ✅ What Was Fixed (Sep 27, 2026)

**Issue**: App crashes on Render with:
```
RuntimeError: Cannot run the event loop while another loop is running
AttributeError: 'NoneType' object has no attribute 'append'
```

**Root Cause**: 
- App startup/shutdown hooks were being registered on the ASGI-wrapped app instead of the original aiohttp app
- ASGI wrapper doesn't have aiohttp methods like `on_startup`, `on_shutdown`

**Solution Applied** (see `BE/src/app.py` line 195-217):
1. Keep aiohttp_app reference for startup/shutdown
2. Register hooks on aiohttp_app BEFORE wrapping with Socket.io
3. Pass ASGI-wrapped app to `web.run_app()`

## 🧪 Test Procedures

### 1. Check Deployment Status

Go to Render dashboard:
- **Service**: game-theory-gateway
- **Check**: Logs tab for any errors
- **Success indicator**: "Starting server on 0.0.0.0:5000"

### 2. Test Health Endpoint

```bash
curl https://game-theory-gateway.onrender.com/health
# Expected: {"status":"ok"}
```

### 3. Test Socket.io Connection

**Option A: Using Node.js Script**

```bash
cd FE
npm install socket.io-client

# Create test-socket.js
```

```javascript
// test-socket.js
const io = require('socket.io-client');

const socket = io('https://game-theory-gateway.onrender.com', {
  reconnection: true,
  reconnectionDelay: 1000,
});

socket.on('connect', () => {
  console.log('✅ Connected to server');
  
  // Test join_room
  socket.emit('join_room', {
    room_id: 'TEST_ROOM',
    player_name: 'Test Player'
  });
});

socket.on('join_room_response', (data) => {
  console.log('✅ Join response:', data);
  
  if (data.success) {
    // Test submit_guess
    socket.emit('submit_guess', {
      room_id: 'TEST_ROOM',
      round_id: 1,
      player_id: data.player.player_id,
      player_name: data.player.name,
      guess_number: 50
    });
  }
});

socket.on('submit_guess_response', (data) => {
  console.log('✅ Guess response:', data);
  socket.disconnect();
});

socket.on('error', (err) => {
  console.error('❌ Error:', err);
  socket.disconnect();
});

setTimeout(() => {
  socket.disconnect();
}, 10000);
```

Run it:
```bash
node test-socket.js
```

**Option B: Using Browser Console**

1. Go to https://game-theory-gateway.onrender.com
2. Open DevTools (F12)
3. Go to Console tab
4. Paste:

```javascript
const io = (await import('https://cdn.socket.io/4.5.4/socket.io.js')).io;
const socket = io('https://game-theory-gateway.onrender.com');

socket.on('connect', () => {
  console.log('✅ Connected!');
  socket.emit('join_room', {
    room_id: 'TEST',
    player_name: 'Browser Test'
  });
});

socket.on('join_room_response', (data) => {
  console.log('✅ Response:', data);
});
```

### 4. Test Complete Game Flow

```javascript
// 1. Join room
socket.emit('join_room', {
  room_id: 'CLB30',
  player_name: 'Player A'
});

// 2. After join succeeds, submit guess
socket.emit('submit_guess', {
  room_id: 'CLB30',
  round_id: 1,
  player_id: 'player_a',
  player_name: 'Player A',
  guess_number: 33.5
});

// 3. Calculate result
socket.emit('calculate_result', {
  room_id: 'CLB30',
  round_id: 1
});

// 4. Listen for result
socket.on('round_result_ready', (data) => {
  console.log('✅ Result:', data);
});
```

## 📊 Expected Logs

In Render dashboard, Logs tab should show:

```
INFO - Connected to Redis
INFO - Connected to RabbitMQ
INFO - Application initialized successfully
INFO - Starting server on 0.0.0.0:5000
INFO - Client connected: {sid}
INFO - Join room event from {sid}: {'room_id': 'TEST_ROOM', 'player_name': 'Test Player'}
```

## 🐛 If Still Failing

### Check these in Render Logs:

1. **Redis connection error**
   - Verify REDIS_URL is correct (starts with `rediss://`)
   - Check it's copied from Upstash Dashboard exactly

2. **RabbitMQ connection error**
   - Verify RABBITMQ_URL is correct (starts with `amqps://`)
   - Check it's copied from CloudAMQP exactly

3. **Port binding error**
   - Render assigns port automatically, check env var `PORT`
   - Update `settings.py` if needed: use `os.getenv('PORT', 5000)`

### If event loop error persists:

1. Check if multiple `web.run_app()` calls exist (shouldn't be)
2. Verify `setup()` is called only once
3. Ensure no `asyncio.run()` wrapping around `web.run_app()`

## ✅ Frontend Testing

Once backend is confirmed working:

1. Run FE locally:
```bash
cd FE
npm run dev
# Opens http://localhost:3000
```

2. Go to `/player` page
3. Enter name and room ID (e.g., "CLB30")
4. Should connect and show ✅ status
5. Enter guess number and submit
6. Should see broadcast messages from other players

## 🔍 Debugging Tools

**Check Redis data**:
```bash
# Using Redis CLI via Upstash
# Go to Upstash Dashboard → Console
# Check keys:
keys *
get room:CLB30
get player:*
```

**Check RabbitMQ messages**:
```bash
# Go to CloudAMQP Dashboard
# Check Queues tab for messages
# Look for: game_results, player_guesses queues
```

## 📝 Notes

- Backend is now stateless (all data in Redis)
- Worker processes result calculations from queue
- Socket.io broadcasts results to all connected players in room
- CORS already enabled for all origins
- Health check endpoint: `/health`
- Swagger UI: `/api/docs`

