__version__ = "0.1.0"
__author__ = "Libin, QuestYard HuRAG Team"
__description__ = "SDK, CLI and API for HuRAG"

import yaml
from pathlib import Path

# -- Global Variables --

conf = None
logger = None

# -- Initialization --

from .utilities import dict_to_namespace

try:
    with open(Path.cwd()/"hurag.yaml", "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    conf = dict_to_namespace(conf)
    # TODO: set defaults
except:
    pass

import logging

logger = logging.getLogger("hurag")
logger.propagate = False
logger.setLevel(logging.INFO)
fmt = logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s - %(message)s"
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(fmt)
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

# -- Shortcuts --

__all__ = [
    "conf",
    "logger",
]
