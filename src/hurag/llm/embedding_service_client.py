from functools import wraps
from typing import Any, TypeVar, cast
from collections.abc import Callable, Coroutine, AsyncGenerator
import inspect

from embedding_service.async_embedding_client import AsyncEmbeddingClient
from .. import conf

T = TypeVar(
    "T", bound=Callable[..., Coroutine[Any, Any, Any] | AsyncGenerator[Any, Any]]
)

def with_es_client(
    func: Callable | None = None,
    *,
    base_url: str | None = None,
    timeout: float = 300.0,
    client_arg_name: str = "esclient",
) -> Callable[..., Any]:
    """
    Decorator to inject an embedding client into the decorated function.

    Args:
        base_url (str | None):
            Optional. The base URL of the embedding service. If not provided,
            it defaults to the value in the configuration.
        timeout (float): 
            Timeout for embedding requests. Default is 300.0 seconds.
        client_arg_name (str):
            The name of the client to be injected into. Default is "esclient".

    Returns:
        Callable[..., Any]: The decorated function with an embedding client injected.
    """
    def decorator(func: T) -> T:
        if inspect.isasyncgenfunction(func):
            @wraps(func)
            async def async_gen_wrapper(*args, **kwargs):
                async with AsyncEmbeddingClient(
                    base_url = base_url or f"{conf.llm.embedding}",
                    timeout = timeout,
                ) as embedding_client:
                    kwargs[client_arg_name] = embedding_client
                    async for item in func(*args, **kwargs):
                        yield item
            return cast(T, async_gen_wrapper)
        else:
            func_coro = cast(Callable[..., Coroutine[Any, Any, Any]], func)
            @wraps(func)
            async def async_func_wrapper(*args, **kwargs):
                async with AsyncEmbeddingClient(
                    base_url = base_url or f"{conf.llm.embedding}",
                    timeout = timeout,
                ) as embedding_client:
                    kwargs[client_arg_name] = embedding_client
                    ret = await func_coro(*args, **kwargs)
                return ret
            return cast(T, async_func_wrapper)
    
    if func is not None:
        return decorator(func)
    return decorator
