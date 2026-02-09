from fastapi import APIRouter, HTTPException

from ...schemas import (
    QueryRequest,
    KnowledgeRequest,
    KnowledgeSchema,
)

router = APIRouter(prefix="/v1/hurag", tags=["知识库"])


@router.post("/retrieve", response_model=list[KnowledgeSchema])
async def retrieve_v1(req: QueryRequest):
    """
    从知识库中检索与用户查询相关的知识。

    ## 请求参数

    ```
    {
        "query": str,               # required
        "history": list[str],       # optional, default=[]
        "graph_search": bool|str,   # optional, default="mix"
        "user_path": str|None,      # optional, default=None
    }
    ```

    `graph_search` 参数在 HuRAG 中支持 `bool` 和 `str` 字面量两种数据类型，
    以支持更多图搜索模式，默认值为 `"mix"`，表示图文混搜模式。
    保留 `bool` 类型以保持与早期实验性 API 版本的前后兼容。

    检索模式及对应的 `graph_search` 参数如下：

    |graph_search |检索模式                                                          |
    |-------------|------------------------------------------------------------------|
    |`"naive"`    |（弃用）等同于 `mix`，仅用于兼容前后版本，下一版本中将取消        |
    |`"graph"`    |（弃用）等同于 `mix`，仅用于兼容前后版本，下一版本中将取消        |
    |`"mix"`      |（默认）图文混合检索，执行文本语义检索和关联子图检索，融合二者结果|
    |`"global"`   |在全知识图谱中搜索关联节点和边，按关联强弱返回引用的段落          |
    |`"community"`|在知识图谱相关社区中搜索关联的节点和边并按关联强弱返回引用的段落  |
    |`True`       |（弃用）等同于 `mix`，仅用于兼容前后版本，下一版本中将取消        |
    |`False`      |（弃用）等同于 `mix`，仅用于兼容前后版本，下一版本中将取消        |

    使用 `hurag corpus load` 加载入库的文档仅完成文本分块存储和语义向量化内嵌，
    使用 `hurag graph build` 命令对所有尚未提取知识图谱的库内文档进行图谱构建，
    此后这些文档可用于 `mix` 模式的检索。

    使用 `hurag graph community` 命令对整个知识图谱应用 Leiden 算法生成社区，
    此后这些社区可用于 `global, community` 模式的检索。

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
        mode = "mix" if isinstance(req.graph_search, bool) else req.graph_search

        kns = await retrieve(
            req.query,
            history=req.history if req.history else None,
            user_path=req.user_path,
            mode=mode,
        )
        responses = [KnowledgeSchema.model_validate(kn[0]) for kn in kns]
        for response, kn in zip(responses, kns):
            response.score = kn[1]
        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge", response_model=list[KnowledgeSchema])
async def get_knowledge_by_ids(req: KnowledgeRequest):
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
        return [KnowledgeSchema.model_validate(kn) for kn in kns]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
