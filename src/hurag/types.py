from typing import Any, TypeVar, ParamSpec, TypeAlias, Literal, cast
from collections.abc import Callable, Coroutine
from openai.types import FilePurpose

RetrieveMode = Literal[
    "naive", "graph", "mix", "community", "global", "agentic", "none"
]
DocumentOrder = Literal["title", "date", "org"]
EmbeddingType = Literal["dense_vecs", "sparse_vecs", "colbert_vecs"]
KeywordType = Literal["low_level_keywords", "high_level_keywords"]
# RagMode = Literal["mix", "community", "global", "agentic", "none"]
RagMode = Literal["mix", "community", "global", "none"]  # temporary for v0.3.0

# Moonshot file purpose
FILE_EXTRACT = cast(FilePurpose, "file-extract")
IMAGE = cast(FilePurpose, "image")
VIDEO = cast(FilePurpose, "video")

P = ParamSpec("P")
R = TypeVar("R")
AsyncFunc: TypeAlias = Callable[P, Coroutine[Any, Any, R]]
