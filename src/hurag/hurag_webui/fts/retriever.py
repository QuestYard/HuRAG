from ..services import load_sessions_by_user, load_messages_by_session
from .tokenizer import tokenize, parallel_tokenize

import bm25s


async def build_index_for_user(
    user_id: str,
    batch_size: int = 100,
) -> tuple[bm25s.BM25, list[str]]:
    """
    Build a full-text search index for all sessions of a given user.

    Arguments:
        user_id: The ID of the user.
        batch_size: The number of sessions to process in each batch.

    Returns:
        A tuple containing:
            - An instance of bm25s.BM25 containing the indexed sessions.
            - A list of session IDs corresponding to the indexed sessions.
    """
    sessions = await load_sessions_by_user(user_id)
    session_docs = {
        s.id: f"{s.title}\n{
            '\n'.join([m.content for m in await load_messages_by_session(s.id)])
        }"
        for s in sessions
    }
    corpus = list(session_docs.values())
    tokenized_corpus = parallel_tokenize(corpus, chunk_size=batch_size)

    retriever = bm25s.BM25()
    retriever.index(tokenized_corpus)

    return retriever, [s.id for s in sessions]


def search_sessions(
    retriever: bm25s.BM25,
    session_ids: list[str],
    query: str,
    top_k: int = 10,
) -> list[tuple[str, float]]:
    query_tokens = tokenize([query])
    ss, sc = retriever.retrieve(query_tokens, corpus=session_ids, k=top_k)

    return [(str(sid), float(score)) for sid, score in zip(ss[0], sc[0]) if score > 0.0]
