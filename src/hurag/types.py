from typing import Any, TypeVar, ParamSpec, TypeAlias, Literal
from collections.abc import Callable, Coroutine

RetrieveMode = Literal["naive", "graph", "mix", "community", "global"]

P = ParamSpec("P")
R = TypeVar("R")
AsyncFunc: TypeAlias = Callable[P, Coroutine[Any, Any, R]]
