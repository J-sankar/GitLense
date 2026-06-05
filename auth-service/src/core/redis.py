import redis.asyncio as redis
from typing import Optional
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


class RedisManager:
    def __init__(self):
        self.client: Optional[redis.Redis] = None

    async def init_redis(self):
        try:
            self.client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,  # Limits maximum pool size for this microservice container
                socket_timeout=5.0,
            )
            await self.client.ping()
            logger.info("Redis connection successfull")

        except Exception as e:
            logger.error(f" Redis connection failed: {e}")

    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("Redis connection pool closed.")

    async def publish_event(self,stream_name:str, event_type:str, payload:dict):
        if not self.client:
            logger.error("Redis client not initialized")
            raise RuntimeError("Redis client not initialized")
        event_data = {
            "event_type":event_type,
            **payload
        }
        message_id = await self.client.xadd(
            stream_name, event_data, id="*"
        )
        return message_id
        



redis_manager = RedisManager()
