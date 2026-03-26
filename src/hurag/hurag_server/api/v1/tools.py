from fastapi import APIRouter, HTTPException

from ...schemas import (
    DocumentSchema,
    FileContentSchema,
    KnowledgeSchema,
    EntitySchema,
    RelationSchema,
    VectorSearchRequest,
    GraphSearchRequest,
    GraphSearchResponse,
)


router = APIRouter(prefix="/v1/tools", tags=["工具库"])


# @router.get("/list_communities", response_model=list[CommunitySchema])
# async def list_comms() -> list[CommunitySchema]:
#     """
#     获取当前知识图谱中所有知识社区的列表。
# 
#     ## 请求参数
# 
#     无
# 
#     ## 返回值
# 
#     所有知识社区的列表，每个社区包括两个字段：`id`, `summary`。
# 
#     ```
#     [
#         {
#             "id": int,          # 社区唯一ID
#             "summary": str      # 社区摘要
#         },
#         ...
#     ]
#     ```
#     """
#     from .utils import list_communities
# 
#     try:
#         comms = await list_communities()
#         return [CommunitySchema.model_validate(comm) for comm in comms]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/vector_search", response_model=list[KnowledgeSchema])
async def hybrid_vector_search(req: VectorSearchRequest) -> list[KnowledgeSchema]:
    """
    在向量知识库根据用户查询执行语义相关度搜索。

    ## 请求参数
    ```
    {
        "query": str,                       # 用户查询
        "user_org_path": str | None = None  # 用户所在组织机构路径，默认为 None
        "document_ids": list[str] = list()  # 搜索的文档范围，默认为空列表
        "rerank": bool = False,             # 是否执行重排序，默认 False
        "top_k": int | None = None          # 返回命中段数，默认 None
        "rrf_k": float | None = None        # 双向量混合搜索RRF参数，默认 None
    }
    ```
    
    - `user_org_path`: 用于确定请求用户能见的文档范围，默认为 None，即不提供，
      此时将使用 `hurag.yaml` 中配置的 `app.org_path` 来作为当前用户的组织机构路径，
      即默认为部署 HuRAG 的组织。

    - `document_ids`: 用户直接指定的搜索文档范围，若为空列表，则根据 `user_org_path`
      确定文档范围；否则直接使用该范围进行搜索。

    - `rerank`: 是否对搜索结果重排序，默认不进行重排序，若为 True，则向量搜索取的前
      `2 * top_k` 条进行重排，最终返回前 `top_k` 条。
      重排序可能对搜索速度造成明显影响。

    - `top_k`, `rrf_k`: 搜索算法参数，若不提供，则使用 `hurag.yaml` 中配置的参数值。

    ## 返回值

    按评分高低返回的 top_k 个命中知识段组成的列表，按照得分高低排序：

    ```
    [
        {
            "segment_id": str,                      # 知识段id
            "content": str,                         # 知识段文本
            "metadata": KnowledgeMetadataSchema,    # 知识所在文档元数据
            "score": float                          # (弃用)语义相似度评分
        },
        ...
    ]
    ```

    其中 `KnowledgeMetadataSchema` 为该段落所在文档的元数据，包括以下字段：

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
    if not req.query:
        return []

    from .... import conf
    from ....knowledge_base import _th_scope, load_knowledge_by_segment_ids
    from ....retrievers import vector_search

    user_path = req.user_org_path or str(conf.app.org_path)
    scope = []

    try:
        if req.document_ids:
            from ....dss import rss
            scope = [
                x[0]
                for x in await rss.query(
                    f"""
                    SELECT s.id FROM segments s
                    JOIN documents d ON s.document_id = d.id
                    WHERE d.id IN ({','.join(['%s'] * len(req.document_ids))})
                    """,
                    tuple(req.document_ids),
                )
            ]

        if not req.document_ids or not scope:
            from datetime import datetime
            _, scope = await _th_scope([datetime.today()], user_path)

        top_k = req.top_k if req.top_k is not None else int(conf.retrieval.top_k)
        segs = await vector_search(
            req.query,
            scope=scope,
            top_k=top_k * 2 if req.rerank else top_k,
            rrf_k=req.rrf_k,
        )
        kns = await load_knowledge_by_segment_ids(segs)

        if req.rerank:
            from ....retrievers import rerank_knowledge
            rr = (await rerank_knowledge(req.query, kns))[:top_k]
            responses = [KnowledgeSchema.model_validate(kn[0]) for kn in rr]
        else:
            rr = list(dict.fromkeys(kns[k] for k in segs))
            responses = [KnowledgeSchema.model_validate(kn) for kn in rr]
        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph_search", response_model=GraphSearchResponse)
async def fully_graph_search(req: GraphSearchRequest) -> GraphSearchResponse:
    """
    在整个知识图谱中根据用户查询执行图谱搜索。

    ## 请求参数
    ```
    {
        "query": str,                           # 用户查询
        "user_org_path": str | None = None      # 用户所在组织机构路径，默认为 None
        "rerank": bool = False,                 # 是否执行重排序，默认 False
        "top_k_entities": int | None = None     # 返回实体数，默认 None
        "top_k_relations": int | None = None    # 返回关系数，默认 None
        "top_k_segments": int | None = None     # 返回命中段数，默认 None
    }
    ```
    
    - `user_org_path`: 用于确定请求用户能见的文档范围，默认为 None，即不提供，
      此时将使用 `hurag.yaml` 中配置的 `app.org_path` 来作为当前用户的组织机构路径，
      即默认为部署 HuRAG 的组织。

    - `rerank`: 是否对搜索结果重排序，默认 False，重排只针对知识段落，实体与关系不重排。

    - `top_k_entities`, `top_k_relations`, `top_k_segments`: 
      搜索算法参数，若不提供，则使用 `hurag.yaml` 中配置的参数值。

    ## 返回值

    包含 `entities`, `relations`, `knowledge` 三个键的字典，值均为对应搜索结果的列表。

    ```
    {
        "entities": [EntitySchema, ...],        # 搜索到的前 top_k_entities 个知识实体 
        "relations": [RelationSchema, ...],     # 搜索到的前 top_k_relations 对知识关系
        "segments": [KnowledgeSchema, ...]     # 搜索到的前 top_k_segments 段知识段落
    }
    ```

    其中:

    - `EntitySchema` 包括以下字段：

    ```
    {
        "id": str,                      # 实体ID
        "name": str,                    # 实体名称
        "type": str,                    # 实体类型
        "description": str              # 实体描述
    }

    - `RelationSchema` 包括以下字段：

    ```
    {
        "id": str,                      # 关系ID
        "source": str,                  # 关系源节点实体名称
        "target": str,                  # 关系目标节点实体名称
        "type": str,                    # 关系类型
        "description": str,             # 关系描述
        "strength": float               # 关系强度（即权重）
    }

    - `KnowledgeSchema` 包括以下字段：

    ```
    {
        "segment_id": str,                      # 知识段ID
        "content": str,                         # 知识段文本
        "metadata": KnowledgeMetadataSchema,    # 知识所在文档元数据
        "score": float                          # (弃用)语义相似度评分
    }
    ```

    其中 `KnowledgeMetadataSchema` 为该段落所在文档的元数据，包括以下字段：

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
    ```
    """
    if not req.query:
        return GraphSearchResponse()

    from ....retrievers import graph_search

    try:
        e, r, s = await graph_search(**(req.model_dump()))
        response = GraphSearchResponse(
            entities=[EntitySchema.model_validate(x) for x in e],
            relations=[RelationSchema.model_validate(x) for x in r],
            segments=[KnowledgeSchema.model_validate(x) for x in s],
        )
        return response
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
