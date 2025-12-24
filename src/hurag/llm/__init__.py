from functools import wraps
from typing import Callable, Any

from embedding_service.async_embedding_client import AsyncEmbeddingClient
from .. import conf, logger

def with_embedding_client(
    base_url: str | None = None,
    *,
    timeout: float = 300.0,
    client_name: str = "embedder",
) -> Callable[..., Any]:
    """
    Decorator to inject an embedding client into the decorated function.

    Args:
        base_url (str | None):
            The base URL of the embedding service. If None, get one from configuration.
        timeout (float): 
            Timeout for embedding requests. Default is 300.0 seconds.
        client_name (str):
            The name of the client to be injected into. Default is "embedder".

    Returns:
        Callable[..., Any]: The decorated function with an embedding client injected.
    """
    ...


