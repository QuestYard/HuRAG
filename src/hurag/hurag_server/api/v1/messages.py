from fastapi import APIRouter
from ...schemas import MessageSchema
from .... import (
    __version__ as hurag_version,
    __author__ as hurag_author,
    conf,
)

router = APIRouter(prefix="/v1/info", tags=["项目信息"])


@router.get("/", response_model=MessageSchema)
async def welcome():
    """Root endpoint for HuRAG-Server.

    Returns:

        MessageSchema: A simple welcome message.
    """
    return MessageSchema(messages=[f"Welcome to HuRAG-Server {hurag_version}"])


@router.get("/version", response_model=MessageSchema)
async def version():
    """Endpoint to get the version and author of HuRAG.

    Returns:

        MessageSchema: Contains the version and author information.
    """
    return MessageSchema(
        messages=[f"HuRAG-Server v{hurag_version}, From {hurag_author}, 2025-2026."]
    )


@router.get("/organization", response_model=MessageSchema)
async def organization():
    """
    获取当前部署使用 HuRAG 的组织机构路径。

    返回:

        MessageSchema: 当前部署机构的组织机构路径。
    """
    return MessageSchema(messages=[conf.app.org_path])
