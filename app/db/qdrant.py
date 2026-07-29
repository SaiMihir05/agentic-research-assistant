from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# We use the Async client for FastAPI / LangGraph compatibility
qdrant_client = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

COLLECTION_NAME = "research_memory"
EMBEDDING_SIZE = 768  # Gemini text-embedding-004 vector size

async def init_qdrant():
    """Ensure the Qdrant collection exists on startup."""
    try:
        collections = await qdrant_client.get_collections()
        exists = any(c.name == COLLECTION_NAME for c in collections.collections)
        if not exists:
            logger.info(f"Creating Qdrant collection: {COLLECTION_NAME}")
            await qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"Collection {COLLECTION_NAME} created successfully.")
        else:
            logger.info(f"Qdrant collection {COLLECTION_NAME} already exists.")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant: {e}")
