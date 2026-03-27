from __future__ import annotations
from typing import Any, TYPE_CHECKING, cast
from collections.abc import Callable
from openai.types.chat import ChatCompletionMessageParam
from openai import RateLimitError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

if TYPE_CHECKING:
    from openai import AsyncOpenAI, AsyncStream
    from openai.types.chat import ChatCompletion

import asyncio

from contextlib import asynccontextmanager
from functools import wraps
from . import build_messages

_clients: dict[str, AsyncOpenAI] = {}
_clients_lock: asyncio.Lock = asyncio.Lock()


def create_oa_client(
    base_url: str,
    api_key: str,
    timeout: float = 60.0,
    multimodal: bool = False,
) -> AsyncOpenAI:
    import httpx
    from openai import AsyncOpenAI

    _httpx = (
        httpx.AsyncClient(
            timeout=httpx.Timeout(connect=20.0, read=timeout, write=timeout, pool=60.0),
            limits=httpx.Limits(
                max_connections=200,
                max_keepalive_connections=100,
                keepalive_expiry=120.0,
            ),
        )
        if multimodal
        else httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=timeout, write=30.0, pool=10.0),
            limits=httpx.Limits(keepalive_expiry=60.0),
        )
    )
    return AsyncOpenAI(base_url=base_url, api_key=api_key, http_client=_httpx)


async def get_oa_client(
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float = 60.0,
    *,
    multimodal: bool = False,
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
        elif client_name == "multimodal":
            base_url = os.getenv(f"{conf.llm.multimodal}_BASE_URL")
            api_key = os.getenv(f"{conf.llm.multimodal}_API_KEY")

        _timeout = max(300.0, timeout) if multimodal else max(60.0, timeout)

        if not base_url:
            raise ValueError("Base URL not available.")
        if not api_key:
            raise ValueError("API Key not available.")

        _clients[client_name] = create_oa_client(
            base_url=base_url,
            api_key=api_key,
            timeout=_timeout,
            multimodal=multimodal,
        )

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
async def lifespan():
    """Context manager to handle OpenAI clients."""
    try:
        yield
    finally:
        await close_oa_client()


def with_oa_client(
    func=None,
    *,
    base_url=None,
    api_key=None,
    timeout=180.0,
    multimodal=False,
    client_name=None,
    client_arg_name="oaclient",
) -> Callable[..., Any]:
    """
    Decorator to provide an AsyncOpenAI client to the decorated async function.

    Args:
        func: Callable | None -- the function to decorate.
        base_url: str -- base URL for OpenAI API.
        api_key: str -- API key for OpenAI API.
        timeout: float -- request timeout in seconds.
        multimodal: bool -- wheather to use longer timeout.
        client_name: str -- name act as the key in _clients dict. If client_name is
            not provided, then base_url and api_key must be provided and a temperary
            client will be created. Otherwise, get_oa_client will be called to get or
            create a permenant client. base_url and api_key can be None if a client
            with the given client_name is "extraction", "generation" or "multimodal".
        client_arg_name: str -- the name of the parameter to pass the client as.

    Returns:
        Callable[..., Any] -- the decorated function.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _cli = (
                await get_oa_client(
                    base_url=base_url,
                    api_key=api_key,
                    timeout=timeout,
                    multimodal=multimodal,
                    client_name=client_name,
                )
                if client_name
                else create_oa_client(
                    base_url=base_url or "",
                    api_key=api_key or "",
                    timeout=timeout,
                    multimodal=multimodal,
                )
            )
            kwargs[client_arg_name] = _cli
            ret = await func(*args, **kwargs)
            if not client_name:
                await _cli.close()
            return ret

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
)
async def chat_completion(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    *,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
    temperature: float = 0.0,
) -> ChatCompletion:
    """
    Non-blocking chat completion call to OpenAI API.

    Args:
        client: AsyncOpenAI -- pre-created AsyncOpenAI client.
        model: str -- the model to use.
        prompt: str -- the user prompt.
        system_prompt: str | None -- optional system prompt.
        history_messages: list[dict[str, str]] | None -- optional chat history.
        temperature: float -- sampling temperature.

    Returns:
        The chat completion response.
    """
    try:
        messages = build_messages(
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
        )
        response = await client.chat.completions.create(
            model=model,
            messages=cast(list[ChatCompletionMessageParam], messages),
            temperature=temperature,
            stream=False,
        )
        return response
    except Exception:
        raise


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
)
async def chat_stream(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    *,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
    temperature: float = 0.0,
) -> AsyncStream:
    """
    Non-blocking stream chat completion call to OpenAI API.

    Args:
        client: AsyncOpenAI -- pre-created AsyncOpenAI client.
        model: str -- the model to use.
        prompt: str -- the user prompt.
        system_prompt: str | None -- optional system prompt.
        history_messages: list[dict[str, str]] | None -- optional chat history.
        temperature: float -- sampling temperature.

    Returns:
        The chat completion response.
    """
    try:
        messages = build_messages(
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
        )
        response = await client.chat.completions.create(
            model=model,
            messages=cast(list[ChatCompletionMessageParam], messages),
            temperature=temperature,
            stream=True,
        )
        return response
    except Exception:
        raise
