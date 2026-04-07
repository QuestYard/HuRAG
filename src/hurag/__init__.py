__version__ = "0.4.2"
__author__ = "Libin, QuestYard HuRAG Team"
__description__ = "HuRAG, A TH-GraphRAG Application From QuestYard."
__url__ = "https://github.com/QuestYard/HuRAG"

from .utilities import dict_to_namespace
import yaml
import logging
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

load_dotenv(Path.cwd() / ".env")

# -- Global Variables --

logger: logging.Logger = logging.getLogger("hurag")
logger.propagate = False
logger.setLevel(logging.DEBUG)

conf: Any

# -- Initialization --


def load_config() -> Any:
    try:
        config_path = Path.cwd() / "hurag.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = dict_to_namespace(data)

        # Ensure config is not a list (which dict_to_namespace can return)
        if isinstance(config, list):
            raise ValueError("Config file must be a dictionary, not a list")

        if config.milvus.token is None:
            raise ValueError("Missing required configuration: milvus.token")
        if config.milvus.db_name is None:
            raise ValueError("Missing required configuration: milvus.db_name")
        if config.mariadb.user is None:
            raise ValueError("Missing required configuration: mariadb.user")
        if config.mariadb.password is None:
            raise ValueError("Missing required configuration: mariadb.password")
        if config.mariadb.database is None:
            raise ValueError("Missing required configuration: mariadb.database")
        if config.app.extra_docs_dir is None:
            raise ValueError("Missing required configuration: app.extra_docs_dir")
        if config.llm.generation is None:
            raise ValueError("Missing required configuration: llm.generation")
        if config.llm.extraction is None:
            raise ValueError("Missing required configuration: llm.extraction")
        if config.llm.multimodal is None:
            raise ValueError("Missing required configuration: llm.multimodal")
        if config.webui_db.user is None:
            raise ValueError("Missing required configuration: webui_db.user")
        if config.webui_db.password is None:
            raise ValueError("Missing required configuration: webui_db.password")
        if config.webui_db.database is None:
            raise ValueError("Missing required configuration: webui_db.database")

        config.milvus.uri = config.milvus.uri or "http://localhost:19530"
        config.mariadb.host = config.mariadb.host or "localhost"
        config.mariadb.port = config.mariadb.port or 3306
        config.log.log_in_file = bool(config.log.log_in_file)
        config.log.max_bytes = config.log.max_bytes or 10485760
        config.log.backup_count = config.log.backup_count or 5
        config.app.org_path = config.app.org_path or "未知机构"
        config.retrieval.top_k = config.retrieval.top_k or 10
        config.retrieval.top_a = config.retrieval.top_a or 50
        config.retrieval.top_s = config.retrieval.top_s or 20
        config.retrieval.rrf_k = config.retrieval.rrf_k or 60
        config.retrieval.top_g = config.retrieval.top_g or 20
        config.retrieval.max_depth = config.retrieval.max_depth or 1
        config.retrieval.max_comms = config.retrieval.max_comms or 3
        config.retrieval.max_nodes = config.retrieval.max_nodes or 1000
        config.retrieval.top_k_e = config.retrieval.top_k_e or 20
        config.retrieval.top_k_r = config.retrieval.top_k_r or 20
        config.retrieval.top_k_s = config.retrieval.top_k_s or 10
        config.llm.embedding = config.llm.embedding or "http://localhost:8765"
        config.api.host = config.api.host or "0.0.0.0"
        config.api.port = config.api.port or 5000
        config.webui_db.host = config.mariadb.host or "localhost"
        config.webui_db.port = config.mariadb.port or 3306
        config.webui_app.ctx_size = config.webui_app.ctx_size or "large"
        config.webui_app.host = config.webui_app.host or "0.0.0.0"
        config.webui_app.port = config.webui_app.port or 8000

        return config

    except ValueError as ve:
        raise ve
    except Exception as e:
        raise RuntimeError(f"Config file not exists or invalid: {e}")


# Load configuration
conf = load_config()

# Configure Logger Handlers
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
    "conf",
    "logger",
    "change_console_log_handler",
    "reset_console_log_handler",
]
