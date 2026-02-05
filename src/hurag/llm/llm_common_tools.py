from __future__ import annotations
from typing import get_args, TYPE_CHECKING

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion, ChatCompletionChunk

from deprecated import deprecated

def build_messages(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """
    Build messages for chat completion.
    
    Args:
        prompt: str -- the user prompt.
        system_prompt: str | None -- optional system prompt.
        history_messages: list[dict[str, str]] | None -- optional chat history.
        
    Returns:
        list[dict[str, str]] -- the constructed messages.
    """
    from openai.types.chat import ChatCompletionRole
    msgs = []
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
            if m["role"] not in get_args(ChatCompletionRole):
                continue
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": prompt})
    return msgs

@deprecated(
    version="0.2.1",
    reason="Using `extract_from_chat` instead, will be removed at 0.3.0.",
)
def extract_response(
    response: ChatCompletion,
    content_only: bool = True,
) -> str | dict[str, str]:
    """
    Extract the response content from a ChatCompletion object.

    Args:
        response: ChatCompletion: the chat completion response object.
        content_only: bool:
            whether to return only the content string or include the role.

    Returns:
        str | dict[str, str]:
            the extracted content or a dictionary with role and content.
    """
    if response.choices and response.choices[0].message.content is not None:
        return (
            response.choices[0].message.content
            if content_only
            else {
                "role": response.choices[0].message.role,
                "content": response.choices[0].message.content,
            }
        )
    return ""

@deprecated(
    version="0.2.1",
    reason="Using `extract_from_chat` instead, will be removed at 0.3.0.",
)
def extract_chunk(
    chunk: ChatCompletionChunk,
    previous_content: str | None = None,
) -> str:
    """
    Extract the response content from a ChatCompletionChunk object.

    Args:
        chunk: ChatCompletionChunk -- the chat completion chunk object.
        previous_content: str | None -- the previous content to append to.

    Returns:
        str -- the extracted content.
    """
    if chunk.choices and chunk.choices[0].delta.content is not None:
        if previous_content is None:
            return chunk.choices[0].delta.content
        else:
            return f"{previous_content}{chunk.choices[0].delta.content}"
    return ""

def extract_from_chat(
    response: ChatCompletion | ChatCompletionChunk
) -> dict[str, str]:
    from openai.types.chat import ChatCompletion
    if isinstance(response, ChatCompletion):
        return {
            "role": response.choices[0].message.role,
            "content": response.choices[0].message.content or "",
        }
    return {
            "role": response.choices[0].delta.role or "assistant",
            "content": response.choices[0].delta.content or "",
        }
