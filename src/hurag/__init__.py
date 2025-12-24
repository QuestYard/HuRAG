__version__ = "0.1.0"
__author__ = "Libin, QuestYard HuRAG Team"
__description__ = "SDK, CLI and API for HuRAG"
__url__ = "https://github.com/QuestYard/HuRAG"

import yaml
from pathlib import Path

# -- Global Options --

OPTIONS = {}

OPTIONS["chunk"] = {
    "delimiter": "|||||",
    "seg_delimiter": "=====",
    "separators": [r"\n\n", r"\n", r"(?<=[。！？；])", r" "],
}

OPTIONS["kg_extraction_examples"] = 1   # suggested max 3
OPTIONS["kg_max_gleanings"] = 1         # suggested max 3

# -- Global Variables --

conf = None
logger = None

# -- Initialization --

from .utilities import dict_to_namespace

try:
    with open(Path.cwd()/"hurag.yaml", "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    conf = dict_to_namespace(conf)
    if (
        conf.milvus.token is None
        or conf.milvus.db_name is None
        or conf.mariadb.user is None
        or conf.mariadb.password is None
        or conf.mariadb.database is None
        or conf.llm.chat_main is None
    ):
        raise ValueError(
            "Missing required configurations: milvus.token, milvus.db_name, "
            "mariadb.user, mariadb.password, mariadb.database, llm.chat_main "
            "must be provided."
        )
    conf.milvus.uri = conf.milvus.uri or "http://localhost:19530"
    conf.mariadb.host = conf.mariadb.host or "localhost"
    conf.mariadb.port = conf.mariadb.port or 3306
    conf.log.log_in_file = bool(conf.log.log_in_file)
    conf.log.max_bytes = conf.log.max_bytes or 10485760
    conf.log.backup_count = conf.log.backup_count or 5
    conf.app.org_path = conf.app.org_path or "未知机构"
    conf.retrieval.top_k = conf.retrieval.top_k or 10
    conf.retrieval.top_a = conf.retrieval.top_a or 50
    conf.retrieval.top_s = conf.retrieval.top_s or 20
    conf.retrieval.rrf_k = conf.retrieval.rrf_k or 60
    conf.retrieval.top_g = conf.retrieval.top_g or 20
    conf.retrieval.max_depth = conf.retrieval.max_depth or 1
    conf.retrieval.max_comms = conf.retrieval.max_comms or 3
    conf.retrieval.max_nodes = conf.retrieval.max_nodes or 1000
    conf.llm.chat_back = conf.llm.chat_back or conf.llm.chat_main
    conf.llm.embedding = conf.llm.embedding or "http://localhost:8765"
    conf.api.host = conf.api.host or "0.0.0.0"
    conf.api.port = conf.api.port or 5000
except ValueError as ve:
    raise ve
except Exception as e:
    raise RuntimeError(f"Config file not exists or invalid: {e}")

import logging

logger = logging.getLogger("hurag")
logger.propagate = False
logger.setLevel(logging.DEBUG)
fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s - %(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(fmt)
console_handler.setLevel(logging.WARNING)
logger.addHandler(console_handler)
if conf.log.log_in_file:
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        filename=Path.cwd() / "hurag.log",
        maxBytes=conf.log.max_bytes,
        backupCount=conf.log.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

def change_console_log_handler(handler: logging.Handler):
    """Change the console log handler."""
    global logger
    current_handlers = logger.handlers[:]
    for h in current_handlers:
        if not isinstance(h, logging.FileHandler):
            logger.removeHandler(h)
    handler.setFormatter(console_handler.formatter)
    logger.addHandler(handler)

def reset_console_log_handler():
    """Reset the console log handler to default."""
    global logger
    current_handlers = logger.handlers[:]
    for h in current_handlers:
        if not isinstance(h, logging.FileHandler):
            logger.removeHandler(h)
    logger.addHandler(console_handler)

# -- Shortcuts --

__all__ = [
    "OPTIONS",
    "conf",
    "logger",
    "change_console_log_handler",
    "reset_console_log_handler",
]

