import os

from .. import __version__, __author__, __description__, __url__, conf, logger
from ..types import RagMode

# -- Global Variables --

org_path = conf.app.org_path
db_pool_name = "webui"
oa_client_name = "generation"
oa_model_name = os.getenv(f"{conf.llm.generation}_MODEL", "")

# -- Initialization --

# check webui configurations
try:
    if (
        conf.webui_db.user is None
        or conf.webui_db.password is None
        or conf.webui_db.database is None
    ):
        raise ValueError(
            "Missing required configurations: webui_db.user, webui_db.password, "
            "webui_db.database must be provided."
        )
    if conf.webui_app.ctx_size.lower() not in ["tiny", "medium", "large"]:
        conf.webui_app.ctx_size = "large"
    conf.webui_db.host = conf.webui_db.host or "localhost"
    conf.webui_db.port = conf.webui_db.port or 3306
    conf.webui_app.host = conf.webui_app.host or "0.0.0.0"
    conf.webui_app.port = conf.webui_app.port or 8000
except ValueError as ve:
    raise ve
except Exception as e:
    raise RuntimeError(f"Config file not exists or invalid: {e}")


async def init_webui():
    from .constants import INIT_RSS_SCRIPTS
    from ..dss import rss

    try:
        _ = await rss.get_pool(
            host=conf.webui_db.host,
            port=conf.webui_db.port,
            user=conf.webui_db.user,
            password=conf.webui_db.password,
            db=conf.webui_db.database,
            pool_name=db_pool_name,
        )
        await rss.transact(INIT_RSS_SCRIPTS, pool_name=db_pool_name)
        logger.info("HuRAG WebUI database is initialized.")
    except Exception as e:
        logger.error(f"Error while initializing the database of WebUI: {e!r}")
        raise


__all__ = [
    "conf",
    "logger",
    "org_path",
    "db_pool_name",
    "oa_client_name",
    "oa_model_name",
    "init_webui",
    "RagMode",
]
