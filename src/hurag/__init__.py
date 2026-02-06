__version__ = "0.2.1"
__author__ = "Libin, QuestYard HuRAG Team"
__description__ = "SDK, CLI and API for HuRAG"
__url__ = "https://github.com/QuestYard/HuRAG"

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

from .utilities import dict_to_namespace

def load_config() -> Any:
    try:
        config_path = Path.cwd() / "hurag.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        config = dict_to_namespace(data)
        
        # Ensure config is not a list (which dict_to_namespace can return)
        if isinstance(config, list):
            raise ValueError("Config file must be a dictionary, not a list")

        if (
            config.milvus.token is None
            or config.milvus.db_name is None
            or config.mariadb.user is None
            or config.mariadb.password is None
            or config.mariadb.database is None
            or config.llm.generation is None
        ):
            raise ValueError(
                "Missing required configurations: milvus.token, milvus.db_name, "
                "mariadb.user, mariadb.password, mariadb.database, llm.generation "
                "must be provided."
            )
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
        config.llm.extraction = config.llm.extraction or config.llm.generation
        config.llm.embedding = config.llm.embedding or "http://localhost:8765"
        config.api.host = config.api.host or "0.0.0.0"
        config.api.port = config.api.port or 5000
        
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
