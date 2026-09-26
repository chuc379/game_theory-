# Deploy to Render Guide

## Prerequisites

Bạn đã setup:
- ✅ Upstash Redis (REDIS_URL)
- ✅ CloudAMQP RabbitMQ (RABBITMQ_URL)
- ✅ GitHub repo với code

## Step 1: Create Render Services

### 1.1 Create Web Service (Socket.io Gateway)

1. Đăng nhập [render.com](https://render.com)
2. Click **New +** → **Web Service**
3. Connect repo của bạn
4. **Service Settings**:
   - **Name**: `game-theory-gateway`
   - **Runtime**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m src.app`
   - **Instance Type**: Free (hoặc Starter tùy budget)

5. **Environment Variables** (Add these):
   ```
   REDIS_URL: rediss://default:gQAAAAAABJrb...@patient-chimp-301787.upstash.io:6379
   RABBITMQ_URL: amqps://user:password@lemon.rmq.cloudamqp.com/vhost
   ENV: production
   DEBUG: false
   SOCKET_IO_PORT: 5000
   ```

6. Click **Deploy**
   - Wait ~3-5 min for deployment
   - Your gateway URL: `https://game-theory-gateway.onrender.com`

### 1.2 Create Background Worker (Job Service)

1. Click **New +** → **Background Worker**
2. Connect same repo
3. **Service Settings**:
   - **Name**: `game-theory-worker`
   - **Runtime**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m src.worker.game_worker`
   - **Instance Type**: Free

4. **Environment Variables** (Same as gateway):
   ```
   REDIS_URL: rediss://default:gQAAAAAABJrb...@patient-chimp-301787.upstash.io:6379
   RABBITMQ_URL: amqps://user:password@lemon.rmq.cloudamqp.com/vhost
   ENV: production
   DEBUG: false
   WORKER_PORT: 5001
   ```

5. Click **Create Background Worker**
   - This runs continuously in background

## Step 2: Verify Deployment

### Check Gateway Health
```bash
curl https://game-theory-gateway.onrender.com/health
# Expected response: {"status": "ok"}
```

### Test Socket.io Connection

**Option 1: Browser Console**
```javascript
const io = require('socket.io-client');
const socket = io('https://game-theory-gateway.onrender.com', {
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  reconnectionAttempts: 5
});

socket.on('connect', () => {
  console.log('✅ Connected to gateway!');
  
  socket.emit('join_room', {
    room_id: 'CLB30',
    player_name: 'Test Player'
  });
});

socket.on('join_room_response', (data) => {
  console.log('✅ Response:', data);
});

socket.on('error', (error) => {
  console.error('❌ Error:', error);
});
```

**Option 2: Node.js Script**
```bash
npm install socket.io-client

# test.js
const io = require('socket.io-client');
const socket = io('https://game-theory-gateway.onrender.com');

socket.on('connect', () => {
  console.log('Connected!');
  socket.emit('join_room', {
    room_id: 'CLB30',
    player_name: 'Test'
  });
});

socket.on('join_room_response', console.log);
```

### Check Worker Logs
1. Go to Background Worker service
2. Click **Logs** tab
3. Should see: "Worker connected to Redis" + "Worker connected to RabbitMQ"

## Step 3: Test Game Flow

### 1. Player Joins
```javascript
socket.emit('join_room', {
  room_id: 'CLB30',
  player_name: 'Player A'
});
```

### 2. Player Submits Guess
```javascript
socket.emit('submit_guess', {
  room_id: 'CLB30',
  round_id: 1,
  player_id: 'usr_123',
  player_name: 'Player A',
  guess_number: 33.5
});
```

### 3. Calculate Result
```javascript
socket.emit('calculate_result', {
  room_id: 'CLB30',
  round_id: 1
});

// Wait for result broadcast
socket.on('round_result_ready', (data) => {
  console.log('Winner:', data.result.winner);
});
```

## Step 4: Monitor & Debug

### Check Render Logs
- **Gateway**: Service → Logs
- **Worker**: Service → Logs (tail -f)

### Common Issues

**Issue**: "Redis connection timeout"
- **Fix**: Verify REDIS_URL format is correct
- **Check**: `rediss://` not `redis://` (SSL required)

**Issue**: "RabbitMQ connection failed"
- **Fix**: Verify RABBITMQ_URL format
- **Check**: URL starts with `amqps://` for SSL

**Issue**: "CORS error when connecting Socket.io"
- **Fix**: Already configured in code (`cors_allowed_origins="*"`)
- **Add** FE domain to CORS if needed (update `src/app.py` later)

## Step 5: Scaling

### If you need more power:

**Gateway (Socket.io)**:
- Upgrade Instance Type: Standard → Pro ($7/month)
- Can handle 1000+ concurrent connections

**Worker**:
- Keep Free tier (runs in background)
- Or upgrade if calculation slow

**Redis/RabbitMQ**:
- Upstash Free: 10GB, 10K reqs/day ✅
- CloudAMQP Free: Unlimited ✅

## Environment Variables Setup (Summary)

Copy these from your services:

1. **Upstash Redis**:
   - Go to Console → Details
   - Find `REDIS_URL` line
   - Example: `rediss://default:gQAAAAAABJrb...@patient-chimp-301787.upstash.io:6379`

2. **CloudAMQP**:
   - Go to instance → Details
   - Find `AMQP URL` line
   - Example: `amqps://username:password@lemon.rmq.cloudamqp.com/vhost`

3. **Add to Render**:
   - Each service (Gateway + Worker)
   - Environment → Add Variable
   - Paste the URLs

## Next Steps

After deployment is working:
1. Build FE with Socket.io client
2. Connect to `https://game-theory-gateway.onrender.com`
3. Test all game events

## Useful Links

- [Render Docs](https://render.com/docs)
- [Socket.io Client](https://socket.io/docs/v4/client-api/)
- [Upstash Redis](https://upstash.com/docs)
- [CloudAMQP](https://www.cloudamqp.com/docs/)
