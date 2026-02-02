from __future__ import annotations
from typing import Callable, Coroutine, TypeVar, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from openai import AsyncOpenAI, AsyncStream
    from openai.types.chat import ChatCompletion

import asyncio

from contextlib import asynccontextmanager
from functools import wraps
from . import build_messages

T = TypeVar("T", bound=Callable[..., Coroutine[Any, Any, Any]])

_clients: dict[str, AsyncOpenAI] = {}
_clients_lock: asyncio.Lock = asyncio.Lock()

def create_oa_client(
    base_url: str,
    api_key: str,
    timeout: float = 180.0,
    max_retries: int = 3,
) -> AsyncOpenAI:
    import httpx
    from openai import AsyncOpenAI
    return AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        max_retries=max_retries,
        http_client=httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=timeout, write=30.0, pool=10.0),
            limits=httpx.Limits(keepalive_expiry=60.0),
        ),
    )

async def get_oa_client(
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float = 180.0,
    max_retries: int = 3,
    client_name: str = "extraction",
) -> AsyncOpenAI:
    """Get or create an AsyncOpenAI client."""
    import os
    from .. import conf

    global _clients

    if client_name in _clients:
        return _clients[client_name]

    async with _clients_lock:
        if client_name in _clients:
            return _clients[client_name]
        if client_name == "extraction":
            base_url = os.getenv(f"{conf.llm.extraction}_BASE_URL")
            api_key = os.getenv(f"{conf.llm.extraction}_API_KEY")
        elif client_name == "generation":
            base_url = os.getenv(f"{conf.llm.generation}_BASE_URL")
            api_key = os.getenv(f"{conf.llm.generation}_API_KEY")
        _clients[client_name] = create_oa_client(base_url, api_key, timeout, max_retries)

    return _clients[client_name]

async def close_oa_client(client_name: str | None = None) -> None:
    """Close the AsyncOpenAI client."""
    global _clients
    if client_name:
        if client_name in _clients:
            client = _clients.pop(client_name)
            await client.close()
    else:
        for client in _clients.values():
            await client.close()
        _clients.clear()

@asynccontextmanager
async def lifespan(app=None):
    """Context manager to handle OpenAI clients."""
    try:
        yield
    finally:
        await close_oa_client()

async def chat(
    model: str,
    prompt: str,
    *,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
    stream: bool = False,
    client: AsyncOpenAI | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.0,
    timeout: float = 60.0,
    max_retries: int = 3,
) -> ChatCompletion | AsyncStream:
    """
    Non-blocking chat completion call to OpenAI API.

    The client can be provided directly, or created using base_url and api_key.

    Args:
        model: str -- the model to use.
        prompt: str -- the user prompt.
        system_prompt: str | None -- optional system prompt.
        history_messages: list[dict[str, str]] | None -- optional chat history.
        stream: bool -- whether to return a streaming response.
        client: AsyncOpenAI | None -- optional pre-created client.
        base_url: str | None -- base URL for OpenAI API.
        api_key: str | None -- API key for OpenAI API.
        temperature: float -- sampling temperature.
        timeout: float -- request timeout in seconds.
        max_retries: int -- maximum number of retries for failed requests.

    Returns:
        str -- the chat completion response.
    """
    should_close = False
    if client is None: 
        if not all([base_url, api_key]):
            raise ValueError("client or base_url/api_key must be provided.")
        client = create_oa_client(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        should_close = True

    try:
        messages = build_messages(
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
        )

        if stream:
            astream = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            if should_close:
                async def stream_wrapper():
                    try:
                        async for chunk in astream:
                            yield chunk
                    finally:
                        await client.close()
                return stream_wrapper()
            return astream
        else:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            if should_close:
                await client.close()
            return response
    except Exception:
        if should_close:
            await client.close()
        raise

def with_oa_client(
    func: Callable | None = None,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    client_name: str | None = None,
    timeout: float = 180.0,
    max_retries: int = 3,
    client_arg_name: str = "oaclient"
) -> Callable[..., Any]:
    """
    Decorator to provide an AsyncOpenAI client to the decorated async function.

    Args:
        func: Callable | None -- the function to decorate.
        base_url: str -- base URL for OpenAI API.
        api_key: str -- API key for OpenAI API.
        client_name: str -- name act as the key in _clients dict. If client_name is
            not provided, then base_url and api_key must be provided and a temperary
            client will be created. Otherwise, get_oa_client will be called to get or
            create a permenant client. base_url and api_key can be None if a client
            with the given client_name is "extraction" or "generation".
        timeout: float -- request timeout in seconds.
        max_retries: int -- maximum number of retries for failed requests.
        client_arg_name: str -- the name of the parameter to pass the client as.

    Returns:
        Callable[..., Any] -- the decorated function.
    """
    def decorator(func: T) -> T:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _cli = await get_oa_client(
                base_url,
                api_key,
                timeout,
                max_retries,
                client_name,
            ) if client_name else create_oa_client(
                base_url=base_url,
                api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
            )
            kwargs[client_arg_name] = _cli
            ret = await func(*args, **kwargs)
            if not client_name:
                _cli and await _cli.close()
            return ret
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator

from openai import RateLimitError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
)
async def chat_with_retry(*args, **kwargs) -> ChatCompletion | AsyncStream:
    # Disable internal retries of the client to avoid nested retries
    # and let tenacity handle the backoff strategy fully.
    kwargs["max_retries"] = 0
    return await chat(*args, **kwargs)

