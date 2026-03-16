from fastapi import APIRouter, HTTPException

from ...schemas import CommunitySchema, DocumentSchema


router = APIRouter(prefix="/v1/tools", tags=["工具库"])


@router.get("/communities", response_model=list[CommunitySchema])
async def communities() -> list[CommunitySchema]:
    """
    获取当前知识图谱中所有知识社区的列表。

    ## 请求参数

    无

    ## 返回值

    所有知识社区的列表，每个社区包括两个字段：`id`, `summary`。

    ```
    [
        {
            "id": int, 社区唯一ID,
            "summary": str, 社区摘要
        },
        ...
    ]
    ```
    """
    from ....agentic import list_communities

    try:
        comms = await list_communities()
        return [CommunitySchema.model_validate(comm) for comm in comms]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=list[DocumentSchema])
async def documents(user_org_path: str) -> list[DocumentSchema]:
    """
    获取当前知识库中所有知识文档的列表。

    ## 请求参数

    user_org_path: str, 用户所在组织机构的路径

    根据用户所在组织机构路径，返回的文档列表中将过滤掉在该机构不生效的文档。

    多模态文档可以获取全文内容供智能体使用，但不能使用向量化搜索来定位文本段落，
    也不支持知识图谱搜索。

    非多模态文档不能获取全文，但可以通过语义相似度搜索文本段落，也支持知识图谱搜索。

    ## 返回值

    所有知识文档的列表，包括该文档所有附件的列表。

    ```
    [
        {
            "id": str, 文档唯一ID,
            "title": str, 文档标题,
            "sn": str | None, 法令号或文号, 若无则为 None,
            "date": datetime, 发布日期,
            "pub_path": str, 文档发布路径,
            "valid_from": datetime, 生效日期,
            "valid_to": datetime | None, 废止日期, 未废止则为 None,
            "replaces": str | None, 上一版本文档标题, 若无则为 None,
            "localizes": str | None, 上位版本文档标题, 若无则为 None,
            "authors": str | None, 作者, 若无则为 None,
            "is_multimodal": bool, 是否为多模态文档,
            "attachments": list[AttachmentSchema], 附件列表
        },
        ...
    ]
    ```

    其中 `AttachmentSchema` 为文档附件结构：
    ```
    {
        "id": str, 附件唯一ID,
        "title": str, 附件标题,
        "document_id": str, 附件所属正文文档的唯一ID
    }
    ```

    所有附件均为多模态文档。
    """
    from ....agentic import list_documents

    try:
        docs = await list_documents(user_org_path)
        return [DocumentSchema.model_validate(doc) for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
