from functools import wraps
from typing import Any
from collections.abc import Callable
import inspect

from .. import conf

# -- Schemas for calling Embedding Service API --

from pydantic import BaseModel, Field

class EmbeddingRequest(BaseModel):
    sentences: list[str] | str = Field(examples=[["What is LLM", "Something amazing"]])
    batch_size: int | None = Field(default=None, examples=[16])
    return_dense: bool = Field(default=True)
    return_sparse: bool = Field(default=False)
    return_colbert_vecs: bool = Field(default=False)
    instruction: str | None = Field(
        default=None, examples=["Embed sentences for retrieval:"]
    )

class RerankRequest(BaseModel):
    query: str = Field(examples=["What is LLM"])
    documents: list[str] | str = Field(
        examples=[["That is an LLM", "Something amazing", "Large Language Model"]]
    )
    query_instruction: str | None = Field(default=None, examples=["Query:"])
    passage_instruction: str | None = Field(default=None, examples=["Passages:"])
    batch_size: int | None = Field(default=None, examples=[4])
    max_length: int | None = Field(default=None, examples=[2048])
    normalize: bool | None = Field(default=None, examples=[True])

class CSRMeta(BaseModel):
    nnz: int
    shape: tuple[int, int]
    dtype: str

class ColBertMeta(BaseModel):
    count: int
    shapes: list[tuple[int, ...]]
    dtype: str

class EmbeddingPayloadMeta(BaseModel):
    has_dense: bool
    dense_shape: tuple[int, int] | None = None
    dense_dtype: str | None = None
    has_sparse: bool
    sparse_meta: CSRMeta | None = None
    has_colbert: bool
    colbert_meta: ColBertMeta | None = None
    format_version: str = "npz_v1"

class RerankResponse(BaseModel):
    scores: list[float] | None = None

# -- The utility function for unpacking embedding responses from binary stream --

def unpack_unified_embeddings_from_bytes(
    npz_bytes: bytes,
) -> tuple[dict, EmbeddingPayloadMeta]:
    """
    Unpack unified embeddings and meta from a compressed .npz bytes stream.

    The returned dictionary will have the following keys:
    - "dense_vecs": numpy.ndarray | None
    - "sparse_vecs": scipy.sparse.csr_matrix | None
    - "colbert_vecs": list[numpy.ndarray] | None

    The returned meta is an instance of EmbeddingPayloadMeta schema.

    It's used to parse http request payloads containing packed embeddings.

    Args:
        npz_bytes (bytes): A .npz packed bytes object containing the embeddings.

    Returns:
        tuple: A tuple containing:
            - dict: A unified embeddings dictionary.
            - EmbeddingPayloadMeta: The metadata of the embeddings.
    """
    import io
    import numpy as np
    from scipy.sparse import csr_matrix

    buf = io.BytesIO(npz_bytes)
    npz = np.load(buf, allow_pickle=False)

    meta_json = npz["meta"].tolist().decode("utf-8")
    meta = EmbeddingPayloadMeta.model_validate_json(meta_json)

    dense = None
    sparse = None
    colbert = None

    if meta.has_dense:
        dense = np.asarray(
            npz["dense_data"], dtype=meta.dense_dtype).reshape(meta.dense_shape)

    if meta.has_sparse:
        data = npz["sparse_data"].astype(meta.sparse_meta.dtype)
        indices = npz["sparse_indices"].astype(np.int32)
        indptr = npz["sparse_indptr"].astype(np.int32)
        shape = tuple(meta.sparse_meta.shape)
        sparse = csr_matrix((data, indices, indptr), shape=shape)

    if meta.has_colbert:
        cm = meta.colbert_meta
        count = int(cm.count)
        dtype = cm.dtype
        colbert = []
        for i in range(count):
            shape = tuple(cm.shapes[i])
            raw = npz[f"colbert_{i}"]
            arr = np.asarray(raw, dtype=dtype).reshape(shape)
            colbert.append(arr)

    return {
        "dense_vecs": dense,
        "sparse_vecs": sparse,
        "colbert_vecs": colbert,
    }, meta

# -- The client class --

import httpx

class AsyncEmbeddingClient:
    """Asynchronous client for embedding and reranking services."""

    def __init__(self, base_url: str, timeout: float = 300.0):
        self.base_url = base_url.strip().rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.timeout, limits=httpx.Limits(max_connections=10)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _ensure_client(self):
        if not self._client:
            raise RuntimeError(
                "Client not initialized. Use 'async with' context manager."
            )

    async def embed(
        self,
        sentences: str | list[str],
        batch_size: int | None = None,
        return_dense: bool = True,
        return_sparse: bool = False,
        return_colbert_vecs: bool = False,
        instruction: str | None = None,
    ) -> tuple[dict, EmbeddingPayloadMeta]:
        """
        Get embeddings for the given sentences (unified format with metadata).

        Args:
            sentences (str | list[str]):
                A single sentence or a list of sentences to encode.
            batch_size (int | None):
                The batch size for encoding.
            return_dense (bool):
                Whether to return dense embeddings.
            return_sparse (bool):
                Whether to return sparse embeddings.
            return_colbert_vecs (bool):
                Whether to return ColBERT vectors.
            instruction (str | None):
                The embed instruction for queries, NOT for documents.

        Returns:
            tuple[dict, EmbeddingPayloadMeta]:
                A tuple containing:
                - A dictionary with the encoded embeddings.
                - An EmbeddingPayloadMeta object with metadata.
        """
        self._ensure_client()

        request = EmbeddingRequest(
            sentences=sentences,
            batch_size=batch_size,
            return_dense=return_dense,
            return_sparse=return_sparse,
            return_colbert_vecs=return_colbert_vecs,
            instruction=instruction,
        )

        async with self._client.stream(
            "POST", f"{self.base_url}/embed", json=request.model_dump()
        ) as response:
            response.raise_for_status()

            chunks = []
            async for chunk in response.aiter_bytes(chunk_size=8192):
                chunks.append(chunk)

            packed_bytes = b"".join(chunks)

        embd, meta = unpack_unified_embeddings_from_bytes(packed_bytes)
        return embd, meta

    async def rerank(
        self,
        query: str,
        documents: str | list[str],
        query_instruction: str | None = None,
        passage_instruction: str | None = None,
        batch_size: int | None = None,
        max_length: int | None = None,
        normalize: bool | None = None,
    ) -> RerankResponse:
        """
        Rerank documents based on their relevance to the query.

        Args:
            query (str):
                The query string to compare against documents.
            documents (str | list[str]):
                A single document or a list of documents to be reranked.
            query_instruction (str | None):
                Instruction for queries.
            passage_instruction (str | None):
                Instruction for passages.
            batch_size (int | None):
                The batch size for processing documents.
            max_length (int | None):
                The max length of context.
            normalize (bool | None):
                Whether to normalize the scores.

        Returns:
            RerankResponse:
                An RerankResponse object containing the reranked scores.
        """
        self._ensure_client()

        request = RerankRequest(
            query=query,
            documents=documents,
            query_instruction=query_instruction,
            passage_instruction=passage_instruction,
            batch_size=batch_size,
            max_length=max_length,
            normalize=normalize,
        )

        response = await self._client.post(
            f"{self.base_url}/rerank", json=request.model_dump()
        )
        response.raise_for_status()

        return RerankResponse.model_validate(response.json())


# -- Decorator for Embedding Service --

def with_es_client(
    func,
    *,
    base_url=None,
    timeout=300.0,
    client_arg_name="esclient",
) -> Callable[..., Any]:
    """
    Decorator to inject an embedding client into the decorated function.

    Args:
        base_url (str | None):
            Optional. The base URL of the embedding service. If not provided,
            it defaults to the value in the configuration.
        timeout (float): 
            Timeout for embedding requests. Default is 300.0 seconds.
        client_arg_name (str):
            The name of the client to be injected into. Default is "esclient".

    Returns:
        Callable[..., Any]: The decorated function with an embedding client injected.
    """
    def decorator(func):
        if inspect.isasyncgenfunction(func):
            @wraps(func)
            async def async_gen_wrapper(*args, **kwargs):
                async with AsyncEmbeddingClient(
                    base_url = base_url or f"{conf.llm.embedding}",
                    timeout = timeout,
                ) as embedding_client:
                    kwargs[client_arg_name] = embedding_client
                    async for item in func(*args, **kwargs):
                        yield item
            return async_gen_wrapper
        else:
            @wraps(func)
            async def async_func_wrapper(*args, **kwargs):
                async with AsyncEmbeddingClient(
                    base_url = base_url or f"{conf.llm.embedding}",
                    timeout = timeout,
                ) as embedding_client:
                    kwargs[client_arg_name] = embedding_client
                    ret = await func(*args, **kwargs)
                return ret
            return async_func_wrapper
    
    if func is not None:
        return decorator(func)
    return decorator
