import logging

from qdrant_client import AsyncQdrantClient, models

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize a global client to be imported by  workers and indexers
qdrant_client = AsyncQdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
)


async def _ensure_tenant_payload_indexes(collection_name: str) -> None:
    """Install idempotent payload indexes required by filtered retrieval."""
    # `is_tenant=True` tells Qdrant to co-locate points for the same tenant,
    # reducing disk reads for the mandatory user_id filter. It is an execution
    # optimization; retrieval still supplies user_id in every Filter.must.
    await qdrant_client.create_payload_index(
        collection_name=collection_name,
        field_name="user_id",
        field_schema=models.KeywordIndexParams(
            type=models.KeywordIndexType.KEYWORD,
            is_tenant=True,
        ),
        wait=True,
    )
    # Visual retrieval also preserves its document-level selection filter.
    await qdrant_client.create_payload_index(
        collection_name=collection_name,
        field_name="document_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
        wait=True,
    )


async def setup_qdrant_collections() -> None:
    """Create and configure the visual collection for multi-tenant search."""
    collection_name = getattr(
        settings, "qdrant_visual_collection_name", "documents_visual"
    )

    try:
        exists = await qdrant_client.collection_exists(collection_name)
        if not exists:
            logger.info(
                "Creating Qdrant multi-vector collection: '%s'...", collection_name
            )
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

        # Run even if the collection predates this release; Qdrant handles
        # create-index calls idempotently and upgrades the desired schema.
        await _ensure_tenant_payload_indexes(collection_name)

        logger.info(
            "Successfully configured Qdrant visual collection '%s'.", collection_name
        )

    except Exception as e:
        logger.error(f"Failed to setup Qdrant collections: {e}")
        raise


async def close_qdrant_client() -> None:
    """Release the startup client's HTTP connection pool at application exit."""
    await qdrant_client.close()
