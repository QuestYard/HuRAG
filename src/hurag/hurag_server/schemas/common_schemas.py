from pydantic import BaseModel, Field

class MessageSchema(BaseModel):
    messages: list[str] = Field(default_factory=list)

class ChatRequest(BaseModel):
    prompt: str = Field(examples=["hello"])
    system_prompt: str | None = Field(
        default=None, examples=["You are a helpful assistant."]
    )
    history: list[dict[str, str]] = Field(
        default_factory=list,
        examples=[
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "Hello, what can I help you?"},
            ],
        ]
    )
    temperature: float = Field(default=0, ge=0, le=1)
    stream: bool = Field(default=True, description="是否采用流式返回")
    timeout: int = Field(default=180, description="调用超时时限(秒)")

class ChatResponse(BaseModel):
    role: str = Field(default="assistant")
    content: str = Field(default="")
