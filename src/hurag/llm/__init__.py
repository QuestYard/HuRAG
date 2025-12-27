from .embedding_service_client import with_es_client
from .embedder import (
    embed_documents,
    embed_query,
)

__all__ = [
    "with_es_client",
    "embed_documents",
    "embed_query",
]

