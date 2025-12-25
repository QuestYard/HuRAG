from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

from embedding_service.async_embedding_client import AsyncEmbeddingClient
from .. import conf, logger

T = TypeVar("T", bound=Callable[..., Coroutine[Any, Any, Any]])

def with_embedding_client(
    func: Callable | None = None,
    *,
    base_url: str | None = None,
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
    def decorator(func: T)-> T:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with AsyncEmbeddingClient(
                base_url = base_url or f"{conf.llm.embedding}",
                timeout = timeout,
            ) as embedding_client:
                kwargs[client_name] = embedding_client
                ret = await func(*args, **kwargs)
            return ret
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator

