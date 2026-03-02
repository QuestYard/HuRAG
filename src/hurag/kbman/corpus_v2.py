from typing import Any
from pathlib import Path
from .. import conf


def corpus_markup_v2(path: str) -> dict[str, Any]:
    """
    Generate markup file `corpus.json` for documents in the given corpus directory.
    1. Scan the directory for all files except `*.idx`, `meta.json` and `corpus.json`;
    2. For each file, create the metadata entry;
    3. Using metadata in `meta.json` if exists;
    4. Generate the markup dict and save into `corpus.json`

    The structure of `corpus.json` is like:
    ```
    {
        "insert": {
            "filename": { metadata },
            ...
        },
        "update": {},
        "delete": []
    }
    ```

    The values of `update` and `delete` leaves empty.

    Args:
        path (str): Path to the corpus directory

    Returns:
        dict[str, Any]: Dict of `corpus.json`
    """
    import json
    from datetime import datetime

    markups = {"insert": {}, "update": {}, "delete": []}
    metadata = []

    corpus = Path(path).expanduser().resolve()
    if not corpus.exists() or not corpus.is_dir():
        return markups
    meta_file = corpus / "meta.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    metadata = {x["filename"]: x for x in metadata}

    for file in corpus.iterdir():
        if not file.is_file():
            continue
        if file.suffix.lower() == ".idx":
            continue
        if file.name.lower() in ["meta.json", "corpus.json"]:
            continue
        if file.name.startswith("."):
            continue

        meta = metadata.get(file.name, {})
        title = file.stem.split("_")[-1]
        if not title.startswith("《"):
            title = f"《{title}"
        if not title.endswith("》"):
            title = f"{title}》"
        markup = {
            "title": meta.get("title", title),
            "sn": meta.get("sn", None),
            "date": meta.get("date", f"{datetime.today():%Y-%m-%d}"),
            "valid_from": meta.get("valid_from", f"{datetime.today():%Y-%m-%d}"),
            "valid_to": meta.get("valid_to", None),
            "replaces": meta.get("replaces", None),
            "pub_path": meta.get("pub_path", conf.app.org_path),
            "localizes": meta.get("localizes", None),
            "authors": meta.get("authors", None),
        }
        markups["insert"][file.name] = markup

    markups["insert"] = {k: markups["insert"][k] for k in sorted(markups["insert"])}
    markup_file = corpus / "corpus.json"
    with open(markup_file, "w", encoding="utf-8") as f:
        json.dump(
            markups,
            f,
            indent=4,
            ensure_ascii=False,
            default=lambda x: f"{x:%Y-%m-%d}" if isinstance(x, datetime) else x,

        )
    return markups


def corpus_split_v2():
    ...
