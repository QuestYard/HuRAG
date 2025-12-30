from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion, ChatCompletionChunk

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

def extract_response(
    response: ChatCompletion,
    content_only: bool = True,
) -> str | dict[str, str]:
    """
    Extract the response content from a ChatCompletion object.

    Args:
        response: ChatCompletion -- the chat completion response object.
        content_only: bool -- whether to return only the content string or include the role.

    Returns:
        str | dict[str, str] -- the extracted content or a dictionary with role and content.
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

