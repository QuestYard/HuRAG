from __future__ import annotations
from typing import (
    AsyncGenerator,
    Callable,
    Coroutine,
    TypeVar,
    Any,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from openai import AsyncOpenAI, AsyncStream

import asyncio
from functools import wraps
from openai.types.chat import ChatCompletionChunk

T = TypeVar("T", bound=Callable[..., Coroutine[Any, Any, Any]])

def create_client(
    base_url: str,
    api_key: str,
    timeout: float = 60.0,
    max_retries: int = 3,
) -> AsyncOpenAI:
    """Create an AsyncOpenAI client."""
    from openai import AsyncOpenAI
    return AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        max_retries=max_retries,
    )

def build_messages(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    if history_messages:
        for m in history_messages:
            if not isinstance(m, dict):
                raise ValueError(
                    "History message must be dict with 'role' and 'content'."
                )
            if "role" not in m or "content" not in m:
                raise ValueError(
                    "History message missing 'role' or 'content'."
                )
            msgs.append(m)
    msgs.append({"role": "user", "content": prompt})
    return msgs

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
) -> str | AsyncStream:
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
        client = create_client(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        should_close = True

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=build_messages(
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
            ),
            temperature=temperature,
        )
        return response.choices[0].message.content
    finally:
        if should_close:
            await client.close()
