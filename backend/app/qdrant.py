import logging

from qdrant_client import AsyncQdrantClient, models

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize a global client to be imported by  workers and indexers
qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)


async def setup_qdrant_collections() -> None:
    """Creates the necessary collections if they do not exist."""
    collection_name = "documents_visual"

    try:
        exists = await qdrant_client.collection_exists(collection_name)
        if exists:
            logger.info(f"Qdrant collection '{collection_name}' already exists.")
            return

        logger.info(f"Creating Qdrant multi-vector collection: '{collection_name}'...")
        await qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=128,  # ColPali patch dimension size
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
            ),
        )

        # Create a payload index for fast lookups by document_id
        await qdrant_client.create_payload_index(
            collection_name=collection_name,
            field_name="document_id",
            field_schema="keyword",
        )

        logger.info("Successfully configured Qdrant visual collection.")

    except Exception as e:
        logger.error(f"Failed to setup Qdrant collections: {e}")
        raise
