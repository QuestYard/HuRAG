from pydantic import BaseModel, Field

class MessageSchema(BaseModel):
    messages: list[str] = Field(default_factory=list)

class ChatRequest(BaseModel):
    prompt: str = Field(..., example="hello")
    system_prompt: str | None = Field(
        default=None, example="You are a helpful assistant."
    )
    history: list[dict[str, str]] = Field(
        default_factory=list, example=[{"role": "user", "content": "hello"}]
    )
    temperature: float = Field(0, ge=0, le=1)
    stream: bool = Field(True, description="是否采用流式返回")
    timeout: int = Field(180, description="调用超时时限(秒)")

class ChatResponse(BaseModel):
    role: str = Field(default="assistant")
    content: str = Field(default="")
