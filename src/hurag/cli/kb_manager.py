import asyncio
import typer

from . import HURAG_EPILOG, show_msg, with_spinner
from .. import logger
from ..dss import init_ds
from ..dss.rss import close_pool

app = typer.Typer(
    help = "QuestYard HuRAG CLI - KnowledgeBase Management Tools",
    add_completion = False,
    epilog = HURAG_EPILOG,
)

@app.command("init", epilog=HURAG_EPILOG)
def init():
    """
    初始化后台知识库，原有数据将被全部清除，请慎重操作。
    """
    ensure = input("初始化将清空数据并重建后端数据库，请输入 Y 确认: ")
    if not ensure.strip().lower().startswith("y"):
        show_msg("用户取消初始化操作", style="info")
        return

    @with_spinner(style="info")
    def _init():
        try:
            asyncio.run(init_ds())
            logger.info("知识库初始化完成")
            show_msg("HuRAG 知识库初始化完成", style="info")
        except Exception as e:
            logger.error(f"知识库初始化失败: {e}")
            show_msg("HuRAG 知识库初始化失败: {e}", style="error", err=e)
        finally:
            asyncio.run(close_pool())

    _init()

@app.command("info", epilog=HURAG_EPILOG)
def info():
    """
    查看当前后台知识库的信息。
    """
    pass
