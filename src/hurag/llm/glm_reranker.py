from __future__ import annotations
from typing import Callable, Coroutine, TypeVar, Any, TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

T = TypeVar("T", bound=Callable[..., Coroutine[Any, Any, Any]])

import os
base_url = os.getenv("GLM_RERANK_BASE_URL")
api_key = os.getenv("GLM_RERANK_API_KEY")
model = os.getenv("GLM_RERANK_MODEL")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

from functools import wraps

def create_httpx_client(timeout: float) -> httpx.AsyncClient:
    """Create an HTTPX AsyncClient."""
    import httpx

    return httpx.AsyncClient(timeout=timeout)

def with_rr_client(
    func: Callable | None = None,
    *,
    timeout: float = 60.0,
    client_name: str = "rrclient",
) -> Callable[..., Any]:
    """
    Decorator to provide a GLM Reranker client to the decorated function.

    The client is created if not already present in the function's keyword arguments.

    Args:
        func: Callable | None -- the function to decorate.
        timeout: float -- timeout for the client.
        client_name: str -- the keyword argument name for the client.

    Returns:
        Callable[..., Any] -- the decorated function.
    """
    def decorator(func: T) -> T:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _cli = create_httpx_client(timeout=timeout)
            kwargs[client_name] = _cli
            ret = await func(*args, **kwargs)
            _cli and await _cli.aclose()
            return ret
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

def should_retry_error(e):
    # Retry on 429 Rate Limit
    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
        return True
    # Retry on connection errors or timeouts (transient network issues)
    if isinstance(
        e, (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout)
    ):
        return True
    return False

@retry(
    retry=retry_if_exception(should_retry_error),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, max=10),
)
async def glm_rerank(
    query: str,
    documents: list[str],
    *,
    post_timeout: float = 30.0,
    client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """
    Rerank documents using GLM Reranker.

    Args:
        query: str -- the query string.
        documents: list[str] -- list of document strings to rerank.
        client: httpx.AsyncClient | None -- optional HTTPX client.

    Returns:
        list[dict[str, Any]] -- list of reranked documents with scores.
            Each dict contains 'index' and 'relevance_score' keys.
    """
    should_close = False
    if client is None:
        client = create_httpx_client(timeout=60.0)
        should_close = True

    try:
        payload = {
            "model": model,
            "query": query,
            "documents": documents,
            "return_raw_scores": True,
        }
        response = await client.post(
            base_url,
            headers=headers,
            json=payload,
            timeout=post_timeout,
        )
        response.raise_for_status()
        result = response.json()
        return result["results"]
    except httpx.HTTPError as e:
        raise e
    except Exception as e:
        raise e
    finally:
        if should_close:
            await client.aclose()

@with_rr_client
async def parallel_glm_rerank(
    query: str,
    documents: list[str],
    rrclient: httpx.AsyncClient | None = None,
    batch_size: int = 2,
    workers: int = 20,
) -> list[float]:
    """
    Rerank documents in parallel using GLM Reranker.

    Args:
        query: str -- the query string.
        documents: list[str] -- list of document strings to rerank.
        rrclient: httpx.AsyncClient | None -- optional HTTPX client.
        batch_size: int -- number of documents per batch.
        workers: int -- number of parallel workers.

    Returns:
        list[float] -- list of relevance scores corresponding to documents.
    """
    import asyncio

    async def _worker(queue: asyncio.Queue):
        nonlocal scores

        while True:
            batch_indices = await queue.get()
            if batch_indices is None:
                queue.task_done()
                return
            batch_docs = [documents[i] for i in batch_indices]
            try:
                reranked = await glm_rerank(
                    query,
                    batch_docs,
                    client=rrclient,
                )
                for score in reranked:
                    scores[batch_indices[score["index"]]] = score["relevance_score"]
            except Exception as e:
                print(f"Failed to rerank batch using GLM: {e!r}")
            finally:
                queue.task_done()

    queue = asyncio.Queue()
    scores = [0.0] * len(documents)
    rerankers = [
        asyncio.create_task(_worker(queue)) for _ in range(workers)
    ]

    for i in range(0, len(documents), batch_size):
        batch_indices = list(range(i, min(i + batch_size, len(documents))))
        await queue.put(batch_indices)

    await queue.join()
    for worker in rerankers:
        worker.cancel()
    gathered = await asyncio.gather(*rerankers, return_exceptions=True)

    return scores
