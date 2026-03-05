import jieba_fast as jieba

jieba.setLogLevel(40)  # Suppress jieba logs


def cleanup(text: str) -> str:
    """
    Cleans the input text (naive version).
    More advanced cleaning can be implemented as needed.
    Must be called both before indexing and querying.
    """
    return text.strip().lower()


def tokenize(corpus: list[str]) -> list[list[str]]:
    """
    Tokenize a list of texts using jieba for search mode.

    Args:
        corpus (list[str]): A list of texts to be tokenized.

    Returns:
        list[list[str]]: A list where each element is a list of tokens.
    """
    if not corpus:
        return []

    return [list(jieba.cut_for_search(cleanup(text))) for text in corpus]


def _tokenize_chunk(args: tuple) -> list[list[str]]:
    """worker: receives (start_idx, chunk_size, corpus)"""
    # warnings.filterwarnings("ignore", category=UserWarning, module="jieba")
    start_idx, size, corpus = args
    # create slice locally in worker (no main memory overhead)
    chunk = corpus[start_idx : start_idx + size]
    return [list(jieba.cut_for_search(cleanup(text))) for text in chunk]


def parallel_tokenize(corpus: list[str], chunk_size: int = 100) -> list[list[str]]:
    """
    Tokenize a list of texts in parallel using jieba for search mode.

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

    def chunk_args_gen():
        for i in range(0, len(corpus), chunk_size):
            yield (i, chunk_size, corpus)

    processes = min(
        max(1, cpu_count() - 1),
        len(corpus) // chunk_size + (len(corpus) % chunk_size != 0),
    )

    with Pool(processes=processes) as pool:
        tokenized_chunks = pool.imap(_tokenize_chunk, chunk_args_gen())

        result = []
        for chunk_tokens in tokenized_chunks:
            result.extend(chunk_tokens)

    return result
