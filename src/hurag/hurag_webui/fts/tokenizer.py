import pkuseg


_seg = None


def _get_seg():
    global _seg
    if _seg is None:
        _seg = pkuseg.pkuseg()
    return _seg


def cleanup(text: str) -> str:
    """
    Cleans the input text (naive version).
    More advanced cleaning can be implemented as needed.
    Must be called both before indexing and querying.
    """
    return text.strip().lower()


def tokenize(corpus: list[str]) -> list[list]:
    """
    Tokenize a list of texts using pkuseg for search mode.

    Args:
        corpus (list[str]): A list of texts to be tokenized.

    Returns:
        list[list[str]]: A list where each element is a list of tokens.
    """
    if not corpus:
        return []

    seg = _get_seg()
    return [seg.cut(cleanup(text)) for text in corpus]


def _init_worker():
    """Initializer for worker processes to ensure clean state."""
    global _seg
    _seg = None


def _tokenize_chunk(chunk: list[str]) -> list[list]:
    """worker: receives chunk (list[str])"""
    seg = _get_seg()
    return [seg.cut(cleanup(text)) for text in chunk]


def parallel_tokenize(corpus: list[str], chunk_size: int = 100) -> list[list[str]]:
    """
    Tokenize a list of texts in parallel using pkuseg for search mode.

    Args:
        corpus (list[str]): A list of texts to be tokenized.
        chunk_size (int): The number of texts to process in each chunk.

    Returns:
        list[list[str]]: A list where each element is a list of tokens.
    """
    if not corpus:
        return []

    if len(corpus) < chunk_size:
        return tokenize(corpus)

    from multiprocessing import Pool, cpu_count

    def chunk_gen():
        for i in range(0, len(corpus), chunk_size):
            yield corpus[i : i + chunk_size]

    processes = min(
        max(1, cpu_count() - 1),
        len(corpus) // chunk_size + (len(corpus) % chunk_size != 0),
    )

    with Pool(processes=processes, initializer=_init_worker) as pool:
        tokenized_chunks = pool.imap(_tokenize_chunk, chunk_gen())

        result = []
        for chunk_tokens in tokenized_chunks:
            result.extend(chunk_tokens)

    return result
