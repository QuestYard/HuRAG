from fastapi import APIRouter, HTTPException

from ...schemas import (
    CommunitySchema,
    DocumentSchema,
    FileContentSchema,
    KnowledgeSchema,
    VectorSearchRequest,
)


router = APIRouter(prefix="/v1/tools", tags=["工具库"])


@router.get("/list_communities", response_model=list[CommunitySchema])
async def list_comms() -> list[CommunitySchema]:
    """
    获取当前知识图谱中所有知识社区的列表。

    ## 请求参数

    无

    ## 返回值

    所有知识社区的列表，每个社区包括两个字段：`id`, `summary`。

    ```
    [
        {
            "id": int,          # 社区唯一ID
            "summary": str      # 社区摘要
        },
        ...
    ]
    ```
    """
    from .utils import list_communities

    try:
        comms = await list_communities()
        return [CommunitySchema.model_validate(comm) for comm in comms]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list_documents", response_model=list[DocumentSchema])
async def list_docs(user_org_path: str) -> list[DocumentSchema]:
    """
    获取当前知识库中所有知识文档的列表。

    ## 请求参数

    - `user_org_path`: str, 用户所在组织机构的路径

    根据用户所在组织机构路径，返回的文档列表中将过滤掉在该机构不生效的文档。

    多模态文档可以获取全文内容供智能体使用，但不能使用向量化搜索来定位文本段落，
    也不支持知识图谱搜索。

    非多模态文档不能获取全文，但可以通过语义相似度搜索文本段落，也支持知识图谱搜索。

    ## 返回值

    所有知识文档的列表，包括该文档所有附件的列表。

    ```
    [
        {
            "id": str,                              # 文档唯一ID
            "title": str,                           # 文档标题
            "sn": str | None,                       # 法令号或文号, 若无则为 None
            "date": datetime,                       # 发布日期
            "pub_path": str,                        # 文档发布路径
            "valid_from": datetime,                 # 生效日期
            "valid_to": datetime | None,            # 废止日期, 未废止则为 None,
            "replaces": str | None,                 # 上一版本文档标题, 若无则为 None
            "localizes": str | None,                # 上位版本文档标题, 若无则为 None
            "authors": str | None,                  # 作者, 若无则为 None
            "is_multimodal": bool,                  # 是否为多模态文档
            "attachments": list[AttachmentSchema]   # 附件列表
        },
        ...
    ]
    ```

    其中 `AttachmentSchema` 为文档附件结构：
    ```
    {
        "id": str,          # 附件唯一ID
        "title": str,       # 附件标题
        "document_id": str  # 附件所属正文文档的唯一ID
    }
    ```

    所有附件均为多模态文档。
    """
    from .utils import list_documents

    try:
        docs = await list_documents(user_org_path)
        return [DocumentSchema.model_validate(doc) for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read_attachment", response_model=FileContentSchema)
async def read_att(id: str) -> FileContentSchema:
    """
    读取指定文档附件的内容。

    ## 请求参数

    - `id`: str, 文档附件的唯一标识ID

    ## 返回值

    ```
    {
        "id": str,          # 文档附件的唯一标识ID,
        "title": str,       # 标题，由主文档标题及附件标题拼接而成,
        "content": str      # 附件的内容
    }
    ```
    """
    from ....dss import rss, fss, AT_FOLDER

    try:
        titles = await rss.query(
            """
            SELECT d.title, a.title FROM attachments AS a JOIN documents AS d
            ON a.document_id = d.id WHERE a.id = %s
            """,
            (id,),
        )
        if not titles:
            raise HTTPException(
                status_code=404, detail=f"Attachment with id '{id}' does not exist."
            )
        title = f"{titles[0][0]}{titles[0][1]}"
        fc = fss.load_files(id, AT_FOLDER)
        if fc[0] is None:
            raise HTTPException(
                status_code=502, detail=f"Retrieve content of '{title}' failed."
            )
        return FileContentSchema(id=id, title=title, content=fc[0].content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read_multimodal_document", response_model=FileContentSchema)
async def read_doc(id: str) -> FileContentSchema:
    """
    读取指定多模态文档的内容。

    ## 请求参数

    - `id`: str, 文档的唯一标识ID

    ## 返回值

    ```
    {
        "id": str,          # 文档的唯一标识ID
        "title": str,       # 文档标题
        "content": str      # 文档的内容
    }
    ```
    """
    from ....dss import rss, fss, MM_FOLDER

    try:
        titles = await rss.query("SELECT title FROM documents WHERE id = %s", (id,))
        if not titles:
            raise HTTPException(
                status_code=404, detail=f"Document with id '{id}' does not exist."
            )
        title = titles[0][0]
        fc = fss.load_files(id, MM_FOLDER)
        if fc[0] is None:
            raise HTTPException(
                status_code=502, detail=f"Retrieve content of '{titles}' failed."
            )
        return FileContentSchema(id=id, title=title, content=fc[0].content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge_search", response_model=list[KnowledgeSchema])
async def vector_search(req: VectorSearchRequest) -> list[KnowledgeSchema]:
    """
    在向量知识库根据用户查询执行语义相关度搜索。

    ## 请求参数
    ```
    {
        "query": str,                       # 用户查询
        "top_k": int,                       # 返回的最大知识段落数, 默认10条
        "rerank": bool,                     # 是否执行重排序，默认 False
        "document_ids": list[str]           # 搜索的文档范围，默认为空列表，即全库搜索
        "user_org_path": str                # 用户所在组织机构路径
    }
    ```
    当请求参数中 `document_ids` 不是空列表时，`user_org_path` 参数将不起作用；否则，
    如果 `document_ids` 为空，则会根据请求参数中的 `user_org_path` 确定搜索范围。

    默认不对向量搜索的结果进行重排序，若 `rerank` 参数设置为 True，则取向量搜索结果的前
    `2 * top_k` 条进行重排，最终返回前 `top_k` 条。

    重排序可能对搜索速度造成明显影响。
    

    ## 返回值

    按评分高低返回的 top_k 个命中知识段组成的列表，按照得分高低排序：

    ```
    [
        {
            "segment_id": str,              # 知识段id
            "content": str,                 # 知识段文本
            "metadata": dict,               # 知识所在文档元数据
            "score": float                  # 语义相似度评分
        },
        ...
    ]
    ```

    其中 `metadata` 以字典形式返回该段落所在文档的元数据，包括以下字段：

    ```
    {
        "id": str,                      # 文档唯一标识符
        "title": str,                   # 文档标题
        "sn": str | None,               # 法令号或文号，非正式发布的法令和文件为 None
        "date": datetime,               # 发布日期
        "valid_from": datetime,         # 生效日期
        "valid_to": datetime | None,    # 废止日期，未废止则为 None
        "replaces": str | None,         # 上一版本标题，若无则为 None
        "pub_path": str,                # 发布机构的组织机构路径
        "localizes": str | None,        # 上位文件标题，若无则为 None
        "authors": str | None,          # 作者，若无则为 None
    }
    """
    from ....retrievers import agentic_search

    await agentic_search(**(req.model_dump()))
    ...
    return []
