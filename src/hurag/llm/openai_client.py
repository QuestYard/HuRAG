from functools import wraps


def with_openai_client(
    func: Callable | None = None,
    *,
    base_url: str,
    api_key: str,
    timeout: float = 300.0,
    client_name: str = "oaclient",
) -> Callable[..., Any]:
    """
    Decorator to inject an openai async_client into the decorated function.

    Args:
        base_url (str | None):
            The base URL of the embedding service. If None, inject None.
    """
