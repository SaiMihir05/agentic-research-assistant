import asyncio
import json
import logging
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize a global Redis connection pool for publishing events
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

async def publish_event(query_id: int, status: str, message: str, data: dict = None):
    """
    Publish a Server-Sent Event (SSE) payload to the Redis channel for a specific query.
    """
    channel = f"query_events:{query_id}"
    payload = {
        "status": status,
        "message": message,
    }
    if data:
        payload["data"] = data

    try:
        await redis_client.publish(channel, json.dumps(payload))
        logger.debug(f"Published event to {channel}: {payload}")
    except Exception as e:
        logger.warning(f"Failed to publish event to Redis for query {query_id}: {e}")

async def subscribe_events(query_id: int):
    """
    Async generator that yields SSE payloads from the Redis channel.
    """
    channel_name = f"query_events:{query_id}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel_name)
    logger.info(f"Subscribed to Redis channel: {channel_name}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                yield {"data": data}
                
                # Check for terminal states to close the stream gracefully
                try:
                    payload = json.loads(data)
                    if payload.get("status") in ["completed", "failed"]:
                        break
                except json.JSONDecodeError:
                    pass
    except asyncio.CancelledError:
        logger.info(f"Client disconnected from SSE stream for query {query_id}")
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()
