import logging
from typing import Optional
import redis.asyncio as aioredis
from ..config import settings

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self):
        self.redis_client = None
        self.in_memory_db = {}

    async def connect(self):
        if settings.redis_url and settings.redis_url.lower() != "memory":
            try:
                self.redis_client = aioredis.from_url(settings.redis_url, socket_timeout=2.0)
                await self.redis_client.ping()
                logger.info("Connected to Redis cache.")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis ({e}). Falling back to in-memory cache.")
                self.redis_client = None
        else:
            logger.info("Using in-memory cache for tag QR codes.")
            self.redis_client = None

    async def get(self, key: str) -> Optional[bytes]:
        if self.redis_client:
            try:
                val = await self.redis_client.get(key)
                return val
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        return self.in_memory_db.get(key)

    async def set(self, key: str, value: bytes, expire: int = None) -> None:
        if self.redis_client:
            try:
                await self.redis_client.set(key, value, ex=expire)
                return
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        self.in_memory_db[key] = value

    async def delete(self, key: str) -> None:
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
                return
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        self.in_memory_db.pop(key, None)


cache = Cache()
