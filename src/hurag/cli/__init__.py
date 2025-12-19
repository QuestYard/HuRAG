from functools import wraps
from typing import Literal, Callable
from rich.console import Console
from rich.theme import Theme

from .. import __version__, __author__, __url__

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

def show_msg(
    msg: str,
    style: Literal["info", "warning", "error", "success", "path"] | None = None,
    err: Exception | None = None,
)-> None:
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
    func: Callable | None = None,
    *,
    text: str = "running...",
    style: str = "bold gray",
    print_result: bool = False,
):
    """
    Decorator: display a sinpper while the decorated function is running.

    Arguments:
        text: spinner prompt text
        style: rich style
        print_result: print return message
    """
    if func is None:
        return lambda f: with_spinner(
            f,
            text = text,
            style = style,
            print_result = print_result,
        )

    @wraps(func)
    def wrapper(*args, **kwargs):
        with console.status(text, spinner_style=style):
            result = func(*args, **kwargs)
        if print_result:
            show_msg(f"Finished: {result}", style=style)
        return result

    return wrapper

def with_async_spinner(
    func: Callable | None = None,
    *,
    text: str = "running...",
    style: str = "bold gray",
    print_result: bool = False,
):
    """
    Decorator: display a sinpper while the decorated async function is running.

    Arguments:
        text: spinner prompt text
        style: rich style
        print_result: print return message
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with console.status(text, spinner_style=style):
                result = await func(*args, **kwargs)
                if print_result:
                    show_msg(f"Finished: {result}", style=style)
                return result
        return wrapper

    if func is not None:
        return decorator(func)

    return decorator

