from __future__ import annotations
from typing import TYPE_CHECKING, Any, AsyncGenerator, Literal

if TYPE_CHECKING:
    from embedding_service.async_embedding_client import AsyncEmbeddingClient
    from embedding_service.schemas import EmbeddingPayloadMeta
    from ..schemas import Document, Graph

from . import with_es_client
from .. import logger

@with_es_client
async def embed_query(
    query: str | list[str],
    *,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> tuple[dict[str, Any], EmbeddingPayloadMeta]:
    """
    Embed a query or a list of queries into vector representations.

    Args:
        query: A single query string or a list of query strings to be embedded.
        return_sparse: Whether to return sparse vectors along with dense vectors.
            Default is True.
        esclient: An instance of AsyncEmbeddingClient. This is provided
            automatically by the decorator.

    Returns:
        A tuple containing:
            - A dictionary with keys "dense_vecs" and "sparse_vecs" containing the
              corresponding vector representations.
            - An EmbeddingPayloadMeta object with metadata about the embeddings.
    """
    try:
        results = await esclient.embed(query, return_sparse=return_sparse)
        return results
    except Exception as e:
        logger.error(f"Failed embedding query: {e}")
        raise

@with_es_client
async def embed_documents(
    docs: Document | list[Document],
    *,
    batch_type: int = 1,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> AsyncGenerator[tuple[dict[str, Any], EmbeddingPayloadMeta], None, None]:
    """
    Embed documents into vector representations in batches.

    Args:
        docs: A single Document object or a list of Document objects to be
            embedded.
        batch_type: The type of batching to use for embedding.
            - 0: all-in-one (embed all chunks from all documents in one batch)
            - 1: doc-by-doc (embed chunks from each document separately)
            - >1: chunk-by-chunk with chunk_size = batch_type
        return_sparse: Whether to return sparse vectors along with dense vectors.
            Default is True.
        esclient: An instance of AsyncEmbeddingClient. This is provided
            automatically by the decorator.

    Yields:
        A tuple containing:
            - A dictionary with keys "dense_vecs" and "sparse_vecs" containing
                the corresponding vector representations for the batch.
            - An EmbeddingPayloadMeta object with metadata about the embeddings.
    """
    from itertools import islice

    if batch_type == 0: # all-in-one
        chunks = [
            chk.text
            for doc in docs
            for seg in doc.segments
            for chk in seg.chunks
        ]
        try:
            results = await esclient.embed(chunks, return_sparse=return_sparse)
            yield results
        except Exception as e:
            logger.error(f"Failed embedding documents: {e}")
            raise
    elif batch_type == 1: # doc-by-doc
        for doc in docs:
            chunks = [chk.text for seg in doc.segments for chk in seg.chunks]
            try:
                results = await esclient.embed(chunks, return_sparse=return_sparse)
                yield results
            except Exception as e:
                logger.error(f"Failed embedding documents: {e}")
                raise
    elif batch_type > 1: # chunk-by-chunk with chunk_size = batch_type
        all_chunks = (
            chk.text
            for doc in docs
            for seg in doc.segments
            for chk in seg.chunks
        )
        while batch := list(islice(all_chunks, batch_type)):
            try:
                results = await esclient.embed(batch, return_sparse=return_sparse)
                yield results
            except Exception as e:
                logger.error(f"Failed embedding documents: {e}")
                raise

@with_es_client
async def embed_keywords(
    keywords: dict[Literal["low_level_keywords", "high_level_keywords"], list[str]],
    *,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> tuple[dict[str, Any], EmbeddingPayloadMeta]:
    """
    Embed keywords into vector representations.

    Args:
        keywords: A dictionary with keys "low_level_keywords" and
            "high_level_keywords", each containing a list of keyword strings
            to be embedded.
        return_sparse: Whether to return sparse vectors along with dense vectors.
            Default is True.
        esclient: An instance of AsyncEmbeddingClient. This is provided
            automatically by the decorator.

    Returns:
        A tuple containing:
            - A dictionary with keys "dense_vecs" and "sparse_vecs" containing
              the corresponding vector representations.
            - An EmbeddingPayloadMeta object with metadata about the embeddings.
    """
    try:
        return await esclient.embed(
            keywords["low_level_keywords"] + keywords["high_level_keywords"],
            return_sparse=return_sparse,
        )
    except Exception as e:
        logger.error(f"Failed embedding keywords: {e}")
        raise

@with_es_client
async def embed_kg_elements(
    g: Graph,
    *,
    return_sparse: bool = True,
    batch_size: int=1024,
    esclient: AsyncEmbeddingClient | None = None,
) -> AsyncGenerator[tuple[dict[str, Any], EmbeddingPayloadMeta], None, None]:
    """
    Embed knowledge graph elements (nodes and edges) into vector representations
    in batches.

    Args:
        g: A Graph object containing the knowledge graph elements to be embedded.
        return_sparse: Whether to return sparse vectors along with dense vectors.
            Default is True.
        batch_size: The number of graph elements to include in each embedding batch.
            Default is 1024.
        esclient: An instance of AsyncEmbeddingClient. This is provided
            automatically by the decorator.

    Yields:
        A tuple containing:
            - A dictionary with keys "dense_vecs" and "sparse_vecs" containing
              the corresponding vector representations for the batch.
            - An EmbeddingPayloadMeta object with metadata about the embeddings.
    """
    from itertools import chain, batched

    for batch in batched(chain(g.nodes, g.edges), batch_size):
        texts = [
            f"## {e.name}: \n\n- {e.description}"
            if hasattr(e, "name")
            else f"## {e.source} - {e.target}:\n\n- {e.description}"
            for e in batch
        ]
        try:
            results = await esclient.embed(texts, return_sparse=return_sparse)
            yield results
        except Exception as e:
            logger.error(f"Failed embedding graph elements: {e}")
            raise

@with_es_client
async def embed_community_summaries(
    summaries: dict[int, list[str]],
    *,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> list[dict[str, Any]]:
    """
    Embed community summarise into vector representations.

    Args:
        summaries: Community summarise returned from `summarize_communities`.
        return_sparse: Whether to return sparse vectors along with dense vectors.
            Default is True.
        esclient: An instance of AsyncEmbeddingClient. This is provided
            automatically by the decorator.

    Returns:
        A list of dictionaries with keys "c_no", "summary", "dense_vecs" and
        "sparse_vecs" containing the communities and their corresponding vector
        representations.
    """
    table = [
        {
            "c_no": k,
            "summary": v[-1] if v else "null",
            "dense_vec": None,
            "sparse_vec": None,
        }
        for k, v in summaries.items()
    ]
    s = [x["summary"] for x in table]
    vecs, _ = await esclient.embed(s, return_sparse=return_sparse)
    for i, e in enumerate(table):
        e["dense_vec"] = vecs["dense_vecs"][i]
        e["sparse_vec"] = vecs["sparse_vecs"][i]

    return table
