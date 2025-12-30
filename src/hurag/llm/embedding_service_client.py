from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar
import inspect

from embedding_service.async_embedding_client import AsyncEmbeddingClient
from .. import conf

T = TypeVar("T", bound=Callable[..., Coroutine[Any, Any, Any]])

def with_es_client(
    func: Callable | None = None,
    *,
    base_url: str | None = None,
    timeout: float = 300.0,
    client_name: str = "esclient",
) -> Callable[..., Any]:
    """
    Decorator to inject an embedding client into the decorated function.

    Args:
        base_url (str | None):
            Optional. The base URL of the embedding service. If not provided,
            it defaults to the value in the configuration.
        timeout (float): 
            Timeout for embedding requests. Default is 300.0 seconds.
        client_name (str):
            The name of the client to be injected into. Default is "esclient".

    Returns:
        Callable[..., Any]: The decorated function with an embedding client injected.
    """
    def decorator(func: T) -> T:
        if inspect.isasyncgenfunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                async with AsyncEmbeddingClient(
                    base_url = base_url or f"{conf.llm.embedding}",
                    timeout = timeout,
                ) as embedding_client:
                    kwargs[client_name] = embedding_client
                    async for item in func(*args, **kwargs):
                        yield item
        else:
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

