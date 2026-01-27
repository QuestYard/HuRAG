from fastapi import APIRouter, HTTPException
# from fastapi.responses import StreamingResponse, JSONResponse

from ...schemas import (
    QueryRequest,
    KnowledgeRequest,
    KnowledgeMetadataSchema,
    KnowledgeSchema,
)

router = APIRouter(prefix="/v1/hurag", tags=["知识库"])

@router.post("/retrieve", response_model=list[KnowledgeSchema])
async def _retrieve(req: QueryRequest):
    """
    从知识库中检索与用户查询相关的知识。

    ## 请求参数

    ```
    {
        "query": str,               # required
        "history": list[str],       # optional, default=[]
        "domains": list[str]|None,  # (deprecated) optional, default=None
        "modes": list[str]|None,    # (deprecated) optional, default=None
        "graph_search": bool|str,   # optional, default="mix"
        "rerank": bool,             # (deprecated) optional, default=True
        "user_path": str|None,      # optional, default=None
    }
    ```

    `domain` 和 `modes` 两个参数在 HuRAG 中已停用，为保持 API 前后兼容，
    仍然可以接受这两个参数，但不会有任何实际作用，通常情况下不要提供即可。

    `graph_search` 参数在 HuRAG 中支持 `bool` 和 `str` 两种数据类型，
    以支持更多图搜索模式，默认值为 `"mix"`，表示图文混搜模式。
    保留 `bool` 类型以保持与早期实验性 API 版本的前后兼容。

    检索模式及对应的 `graph_search` 参数如下：

    |graph_search |检索模式                                                                                                       |重排序|默认top_k|
    |-------------|---------------------------------------------------------------------------------------------------------------|------|---------|
    |`"naive"`    |文本语义检索，在全知识库文本中使用 hybrid search 搜索语义相似的段落                                            |  是  |    10   |
    |`"graph"`    |关联子图检索，根据用户查询提取关键词，在知识图谱中定位语义关联子图，使用 hybrid search 搜索子图中语义相似的段落|  是  |    10   |
    |`"mix"`      |图文混合检索，同时执行文本语义检索和关联子图检索，融合二者结果，返回其中排名最高的段落 **(default)**           |  是  |    10   |
    |`"global"`   |根据用户查询提取关键词，在全知识图谱中搜索关联节点和边，按关联强弱返回引用的段落                               |  否  |    50   |
    |`"community"`|根据用户查询提取关键词，在全知识图谱中定位最多5个相关社区，搜索社区中关联的节点和边并按关联强弱返回引用的段落  |  否  |    50   |
    |`True`       |等同于 `mix`，确保 API 前后版本参数含义和默认模式一致                                                          |  是  |    10   |
    |`False`      |等同于 `naive`，确保 API 前后版本参数含义一致                                                                  |  是  |    10   |

    使用 `hurag corpus load` 加载入库的文档仅完成文本分块存储和语义向量化内嵌，
    此时这些文档仅能用于 `naive` 模式检索。

    使用 `hurag graph build` 命令对所有尚未提取知识图谱的库内文档进行图谱构建，
    此后这些文档可用于 `graph, mix` 模式的检索。

    使用 `hurag graph community` 命令对整个知识图谱应用 Leiden 算法生成社区，
    此后这些社区可用于 `global, community` 模式的检索。

    当无法从用户查询中提取到有意义的关键词时，将强制使用 `naive` 模式。因此，
    建议前端事先判断用户查询是否需要检索知识库以增强生成，若不需要可直接调用
    `v1/llm/chat` API 进行对话。

    `rerank` 参数已经停用，仅为保持 API 前后兼容而保留。HuRAG 中，`naive`,
    `graph`, `mix` 三种模式检索结果自动重排序；`graph` 和 `community`
    模式检索结果不重排序。

    `user_path` 参数为前端可选提供的参数。如果前端接入了用户与组织机构管理，
    则可以通过此参数传递当前用户所在组织机构的路径，规则同文档发布机构路径。
    不提供此参数即采用默认值 None，使用 HuRAG 部署机构相同的路径。

    ## 返回值

    按评分高低返回的 top_k 个命中知识段组成的列表，按照得分高低排序：

    ```
    [
        {
            "segment_id": "知识段id",
            "content": "知识段文本",
            "metadata": {知识所在文档元数据字典},
            "score": 0.9
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
        "pub_path": str,                # 发布路径，详见 HuRAG 说明文档
        "localizes": str | None,        # 上位文件标题，若无则为 None
        "authors": str | None,          # 作者，若无则为 None
    }
    ```
    """
    from ....retrievers import retrieve

    try:
        if isinstance(req.graph_search, bool):
            mode = "mix" if req.graph_search else "naive"
        else:
            mode = req.graph_search

        kns = await retrieve(
            req.query,
            history=req.history if req.history else None,
            user_path=req.user_path,
            mode=mode,
        )
        return [
            KnowledgeSchema(
                segment_id=kn[0].segment_id,
                content=kn[0].content,
                metadata=KnowledgeMetadataSchema(
                    id=kn[0].metadata.id,
                    title=kn[0].metadata.title,
                    sn=kn[0].metadata.sn,
                    date=kn[0].metadata.date,
                    pub_path=kn[0].metadata.pub_path,
                    valid_from=kn[0].metadata.valid_from,
                    valid_to=kn[0].metadata.valid_to,
                    replaces=kn[0].metadata.replaces,
                    localizes=kn[0].metadata.localizes,
                    authors=kn[0].metadata.authors,
                ),
                score=kn[1],
            ) for kn in kns
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge", response_model=list[KnowledgeSchema])
async def _get_knowledge_by_ids(req: KnowledgeRequest):
    """
    根据提供的 id 列表获取知识段。

    ## 请求参数

    ```
    {
        "ids": list[str],       # required, The ids of knowledge (segments)
        "user_path": str|None,  # optional, default=None
    }
    ```

    从知识库中检索请求参数指定的 `ids` 列表所指向的段落，并根据 `user_path`
    进行过滤后，装载为 `Knowledge` 对象并返回。

    ## 返回值

    符合条件的知识段列表：

    ```
    [
        {
            "segment_id": "知识段id",
            "content": "知识段文本",
            "metadata": {知识所在文档元数据字典},
            "score": 0
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
        "pub_path": str,                # 发布路径，详见 HuRAG 说明文档
        "localizes": str | None,        # 上位文件标题，若无则为 None
        "authors": str | None,          # 作者，若无则为 None
    }
    ```
    """
    from ....knowledge_base import get_knowledge_by_segment_ids

    try:
        kns = await get_knowledge_by_segment_ids(req.ids, user_path=req.user_path)
        return [
            KnowledgeSchema(
                segment_id=kn.segment_id,
                content=kn.content,
                metadata=KnowledgeMetadataSchema(
                    id=kn.metadata.id,
                    title=kn.metadata.title,
                    sn=kn.metadata.sn,
                    date=kn.metadata.date,
                    pub_path=kn.metadata.pub_path,
                    valid_from=kn.metadata.valid_from,
                    valid_to=kn.metadata.valid_to,
                    replaces=kn.metadata.replaces,
                    localizes=kn.metadata.localizes,
                    authors=kn.metadata.authors,
                ),
                score=0.0,
            ) for kn in kns
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
