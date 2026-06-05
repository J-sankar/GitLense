import redis.asyncio as redis
from typing import Optional
from src.core.config import settings
from src.core.logger import get_logger
from datetime import datetime, timezone

import contextlib

logger = get_logger(__name__)

STREAM_REPO_FETCH   = "repo:fetch"
STREAM_FILE_PROCESS = "file:process"
STREAM_FILE_STORE   = "file:store"
STREAM_FAILED       = "ingestion:failed"

# consumer groups
GROUP_FETCH   = "fetch-workers"
GROUP_PROCESS = "process-workers"
GROUP_STORE   = "store-workers"

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
                socket_timeout=10.0,
                health_check_interval=30,  # Ping Redis every 30s to keep the connection alive
                socket_connect_timeout=5.0,
            )
            await self.client.ping()
            logger.info("Redis connection successfull")

        except Exception as e:
            logger.error(f" Redis connection failed: {e}")

    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("Redis connection pool closed.")

    async def _init_consumer_groups(self):
        if not self.client:
            logger.error("Redis client not initialized")
            raise RuntimeError("Redis client not initialized")
        for stream, group in [(STREAM_REPO_FETCH,   GROUP_FETCH),
            (STREAM_FILE_PROCESS, GROUP_PROCESS),
            (STREAM_FILE_STORE,   GROUP_STORE),]:
            try:
                await self.client.xgroup_create(stream, group,id="0",mkstream=True)
                logger.info(f"Consumer group created: {group} on {stream}")
            except Exception :
                pass

    async def publish(self,stream_name:str,  payload:dict):
        if not self.client:
            logger.error("Redis client not initialized")
            raise RuntimeError("Redis client not initialized")
        
        message_id = await self.client.xadd(
            stream_name, payload, id="*"
        )
        logger.debug(f"Published to {stream_name}: {message_id}")
        return message_id

    async def consume(self,stream:str,group:str,consumer:str,count:int = 5):
        if not self.client:
            logger.error("Redis client not initialized")
            raise RuntimeError("Redis client not initialized")
        
        results = await self.client.xreadgroup(
            group,
            consumer,
            {stream:">"},
            count,
            block=5000,
        )
        return results or []
    

    async def ack(self,stream:str, group:str,consumer:str, message_id:str):
        if not self.client:
            logger.error("Redis client not initialized")
            raise RuntimeError("Redis client not initialized")
        
        await self.client.xack(stream,group,message_id)
        logger.debug(f"ACKed {message_id} on {stream}")


    async def dead_letter(self, stream_origin:str, data:dict, error:str,reason:str = "max_retires_exceeded" ):
        if not self.client:
            logger.error("Redis client not initialized")
            raise RuntimeError("Redis client not initialized")
        await self.publish(STREAM_FAILED, {
             **data,
            "stream_origin":stream_origin,
            "error": error,
            "failed_at": str(datetime.now(timezone.utc)),
            "reason":reason,
            
        }
        )
        logger.error(
            f"Dead letter: {data.get('file_path'), data.get('repo_url', 'unknown')} "
            f"| reason: {reason} | error: {error[:100]}"
        )

        
    async def reclaim_abandoned(self,stream:str,group:str,consumer:str,min_idle_ms:int = 300000 ) ->list :
        if not self.client:
            logger.error("Redis client not initialized")
            raise RuntimeError("Redis client not initialized")
        try:
            result = await self.client.xautoclaim(stream, group,consumer, min_idle_ms,start_id="0-0", count=10)

            if result and result[1]:
                logger.info(
                    f"Reclaimed {len(result[1])} abandoned messages "
                    f"from {stream}"
                )
                return result[1] 
        except Exception as e:
            logger.error(f"Recovery Failed: {str(e).lower()} ")
        return []




    async def republish_with_retry(
        self,
        stream:  str,
        data:    dict,
        retries: int
    ):
        await self.publish(stream, {
            **data,
            "retries": str(retries)
        })
        logger.info(
            f"Republished to {stream} | "
            f"file: {data.get('file_path', 'unknown')} | "
            f"attempt: {retries}"
        )


    @contextlib.asynccontextmanager
    async def lock(self, lock_name: str, timeout: int = 10):
        """Yields a distributed Redis lock."""
        # Create the lock in Redis (auto-expires in case the worker crashes)
        redis_lock = self.client.lock(lock_name, timeout=timeout)
        
        # Wait until the lock is available
        acquired = await redis_lock.acquire(blocking=True)
        try:
            yield acquired
        finally:
            if acquired:
                await redis_lock.release()

redis_manager = RedisManager()
