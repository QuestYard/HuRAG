from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json

from ...schemas import ChatRequest, ChatResponse
from ....depends import HuragGenerationClient, HuragGenerationModel

router = APIRouter(prefix="/v1/llm", tags=["大模型"])

@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        200: {
            "content": {
                "text/event-stream": {  # 流式 SSE 响应
                    "schema": {
                        "type": "string",
                        "example": "data: {...}\\n\\n..."
                    }
                },
                "application/json": {  # 普通 JSON 响应
                    "schema": ChatResponse.model_json_schema()
                }
            },
            "description": "根据请求参数 stream 返回 JSON 或 SSE"
        }
    }
)
async def _chat(
    req: ChatRequest,
    client: HuragGenerationClient,
    model: HuragGenerationModel,
):
    """
    与本地部署的大模型进行聊天，统一入口。

    ## 请求参数

    ```
    {
        "prompt": str,                      # required
        "system_prompt": str,               # optional, default=None
        "history": list[dict[str, str]],    # optional, default=[]
        "temperature": float,               # optional, default=0
        "stream": bool,                     # optional, default=True
        "timeout": int,                     # optional, default=180
    }
    ```

    其中，history 参数是一个与大模型多次交互产生的对话列表，列表元素为字典：

    ```
    [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hello, how can i help you?"},
        ...
    ]
    ```

    如果不提供对话历史，则不需要提供该参数，或者提供一个空列表而非空值。

    ## 返回值

    如果 `stream == False`，返回一个 JSON 对象：

        {"role": "assistant", "content": str}

    如果 `stream == True`，返回一个 SSE 流，每一次返回的有效内容是一个以
    `"data: "` 开头的 JSON 字符串，结尾最后一次内容为 `"data: [DONE]"` 。

    可以使用以下的 python 程序来迭代获取流式返回的结果：

    ```
    import asyncio
    import httpx

    async def main():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                "http://<server-ip>:<port>/v1/llm/chat",
                json={"prompt": "Hello", "stream": True}
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    payload = line.removeprefix("data: ")
                    if payload == "[DONE]":
                        break
                    print(json.loads(payload)["delta"], end="", flush=True)

    asyncio.run(main())
    ```
    """
    from ....llm import chat, extract_response, extract_chunk

    try:
        resp = await chat(
            model,
            req.prompt,
            system_prompt=req.system_prompt,
            history_messages=req.history,
            stream=req.stream,
            temperature=req.temperature,
            timeout=req.timeout,
            client=client,
        )
        if not req.stream:
            return ChatResponse(content=extract_response(resp))

        async def _sse():
            async for chunk in resp:
                # extract_chunk 返回当前 chunk 的内容增量
                delta = extract_chunk(chunk)
                payload = {"delta": delta}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            _sse(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
