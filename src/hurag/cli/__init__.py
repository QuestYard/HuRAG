from functools import wraps
from typing import Any, Literal, Callable, Coroutine, TypeVar
from rich.console import Console
from rich.theme import Theme
from rich.logging import RichHandler

from .. import (
    __version__,
    __author__,
    __url__,
    change_console_log_handler,
    reset_console_log_handler,
)

T = TypeVar("T", bound=Callable[..., Coroutine[Any, Any, Any]])

HURAG_EPILOG = f"""
HuRAG {__version__}, {__author__}, 2025-2026.

For more info, visit: {__url__}
"""

PREDEFINED_COLORS = {
    "info": "dark_slate_gray2",
    "warning": "orange1",
    "error": "bold bright_red",
    "success": "bright_green",
    "path": "underline turquoise2",
}

console = Console(theme=Theme(PREDEFINED_COLORS))

rich_handler = RichHandler(
    level="WARNING",
    console=console,
    show_level=False,
    show_time=False,
    rich_tracebacks=True,
    tracebacks_show_locals=True,
)

def show_msg(
    msg: str,
    style: Literal["info", "warning", "error", "success", "path"] | None = None,
    err: Exception | None = None,
) -> None:
    """Show message along with exception traceback on the console."""
    console.print(msg, style=style if style in PREDEFINED_COLORS else None)
    if err is not None:
        tb = err.__traceback__
        while tb.tb_next:
            tb = tb.tb_next
        frame = tb.tb_frame
        console.print(f">>> File: {frame.f_code.co_filename}")
        console.print(f">>> Line: {tb.tb_lineno}")
        console.print(f">>> Func: {frame.f_code.co_name}")

def with_spinner(
    func: T | None = None,
    *,
    text: str = "running...",
    style: str = "bold gray",
    print_result: bool = False,
) -> Callable[..., Any]:
    """
    Decorator: display a sinpper while the decorated function is running.

    Arguments:
        text: spinner prompt text
        style: rich style
        print_result: print return message
    """
    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(*args, **kwargs):
            change_console_log_handler(rich_handler)
            with console.status(text, spinner_style=style):
                result = func(*args, **kwargs)
            if print_result:
                show_msg(f"Finished: {result}", style=style)
            reset_console_log_handler()
            return result
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator

def with_async_spinner(
    func: T | None = None,
    *,
    text: str = "running...",
    style: str = "bold gray",
    print_result: bool = False,
) -> Callable[..., Any]:
    """
    Decorator: display a sinpper while the decorated async function is running.

    Arguments:
        text: spinner prompt text
        style: rich style
        print_result: print return message
    """
    def decorator(func: T) -> T:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            change_console_log_handler(rich_handler)
            with console.status(text, spinner_style=style):
                result = await func(*args, **kwargs)
            if print_result:
                show_msg(f"Finished: {result}", style=style)
            reset_console_log_handler()
            return result
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator

def async_cmd(func: T) -> Callable[..., Any]:
    """Decorator to run an async command with database lifespan management."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import asyncio
        from ..dss import rss, vss
        from ..llm import llm_lifespan
        
        async def _runner():
            async with rss.lifespan(), vss.lifespan(), llm_lifespan():
                return await func(*args, **kwargs)
        
        return asyncio.run(_runner())
    return wrapper

def print_regex_literal(regex_pattern: str, label: str | None = None) -> None:
    """
    Print a regex pattern as a literal string without escape character interference.
    
    This function outputs the regex pattern exactly as it would appear in an r-string,
    making it easy to see the actual regex syntax without Python string escaping.
    
    Args:
        regex_pattern: The regex pattern string to display
        label: Optional label to prefix the output for clarity
    """
    if label:
        console.print(f"{label}: ", style="info", end="")
    
    # Use repr() to show the string with proper escaping, similar to r-string behavior
    console.print(repr(regex_pattern), style="path")

