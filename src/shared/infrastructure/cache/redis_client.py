"""
Redis client - Singleton for cache operations
"""
import json
import logging
import redis.asyncio as redis
from typing import Optional, List, Dict, Any
from config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis async client wrapper"""

    _instance: Optional["RedisClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    async def connect(self):
        """Initialize Redis connection"""
        if self._initialized:
            return

        # Use Redis URL if provided (Upstash), otherwise build from components
        if settings.REDIS_URL:
            url = settings.REDIS_URL
            # Add decode_responses parameter if not in URL
            if "?" not in url:
                url += "?decode_responses=True"
            self.client = await redis.from_url(url, decode_responses=True)
        else:
            # Local Redis connection
            self.client = await redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                decode_responses=True,
            )
        self._initialized = True
        logger.info("Redis connected")

    async def disconnect(self):
        """Close Redis connection"""
        if hasattr(self, "client"):
            await self.client.close()
            logger.info("Redis disconnected")

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set key-value pair"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.set(key, value, ex=ttl)

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        return await self.client.get(key)

    async def get_json(self, key: str) -> Optional[dict]:
        """Get value and parse as JSON"""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None

    async def hset(self, key: str, mapping: Dict[str, Any]) -> None:
        """Set hash fields"""
        # Convert nested dicts to JSON
        data = {}
        for k, v in mapping.items():
            if isinstance(v, (dict, list)):
                data[k] = json.dumps(v)
            else:
                data[k] = v
        await self.client.hset(key, mapping=data)

    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field"""
        return await self.client.hget(key, field)

    async def hget_json(self, key: str, field: str) -> Optional[dict]:
        """Get hash field and parse as JSON"""
        value = await self.hget(key, field)
        if value:
            return json.loads(value)
        return None

    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Get all hash fields"""
        data = await self.client.hgetall(key)
        # Parse JSON values
        parsed = {}
        for k, v in data.items():
            try:
                parsed[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                parsed[k] = v
        return parsed

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields"""
        return await self.client.hdel(key, *fields)

    async def delete(self, key: str) -> int:
        """Delete key"""
        return await self.client.delete(key)

    async def lpush(self, key: str, *values: Any) -> int:
        """Push to list"""
        str_values = [json.dumps(v) if isinstance(v, (dict, list)) else str(v) for v in values]
        return await self.client.lpush(key, *str_values)

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get list range"""
        data = await self.client.lrange(key, start, end)
        parsed = []
        for v in data:
            try:
                parsed.append(json.loads(v))
            except (json.JSONDecodeError, TypeError):
                parsed.append(v)
        return parsed

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await self.client.exists(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration"""
        return await self.client.expire(key, seconds)


redis_client = RedisClient()
