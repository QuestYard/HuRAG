from __future__ import annotations
from typing import get_args, TYPE_CHECKING

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
                raise ValueError("History message missing 'role' or 'content'.")
            if m["role"] not in get_args(ChatCompletionRole):
                continue
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": prompt})
    return msgs


def extract_from_chat(response: ChatCompletion | ChatCompletionChunk) -> dict[str, str]:
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
