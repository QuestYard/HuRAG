from typing import Any, TypeVar, ParamSpec, TypeAlias, Literal
from collections.abc import Callable, Coroutine

RetrieveMode = Literal["naive", "graph", "mix", "community", "global", "agentic"]
DocumentOrder = Literal["title", "date", "org"]
EmbeddingType = Literal["dense_vecs", "sparse_vecs", "colbert_vecs"]
KeywordType = Literal["low_level_keywords", "high_level_keywords"]
RagMode = Literal["mix", "community", "global", "agentic", "none"]

P = ParamSpec("P")
R = TypeVar("R")
AsyncFunc: TypeAlias = Callable[P, Coroutine[Any, Any, R]]
