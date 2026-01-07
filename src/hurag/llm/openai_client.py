from __future__ import annotations
from typing import (
    Callable,
    Coroutine,
    TypeVar,
    Any,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from openai import AsyncOpenAI, AsyncStream
    from openai.types.chat import ChatCompletion

from functools import wraps

from . import build_messages

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
        client = create_client(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        should_close = True

    try:
        if stream:
            astream = await client.chat.completions.create(
                model=model,
                messages=build_messages(
                    prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                ),
                temperature=temperature,
                stream=True,
            )
            return astream
        else:
            response = await client.chat.completions.create(
                model=model,
                messages=build_messages(
                    prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                ),
                temperature=temperature,
            )
            return response
    finally:
        if should_close:
            await client.close()

def with_oa_client(
    func: Callable | None = None,
    *,
    base_url: str,
    api_key: str,
    timeout: float = 60.0,
    max_retries: int = 3,
    client_name: str = "oaclient"
) -> Callable[..., Any]:
    """
    Decorator to provide an AsyncOpenAI client to the decorated async function.
    Args:
        func: Callable | None -- the function to decorate.
        base_url: str -- base URL for OpenAI API.
        api_key: str -- API key for OpenAI API.
        timeout: float -- request timeout in seconds.
        max_retries: int -- maximum number of retries for failed requests.
        client_name: str -- the name of the parameter to pass the client as.
    """
    def decorator(func: T) -> T:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _cli = create_client(
                base_url=base_url,
                api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
            )
            kwargs[client_name] = _cli
            ret = await func(*args, **kwargs)
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
async def chat_with_retry(*args, **kwargs):
    # Disable internal retries of the client to avoid nested retries
    # and let tenacity handle the backoff strategy fully.
    kwargs["max_retries"] = 0
    return await chat(*args, **kwargs)

