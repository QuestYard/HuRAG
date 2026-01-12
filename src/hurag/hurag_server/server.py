import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
from contextlib import asynccontextmanager

from .. import logger, conf, __version__ as hurag_version

from .api.v1.messages import router as info_router
# from .api.v1.llm import router as llm_router
# from .api.v1.hurag import router as hurag_router

class LifespanClient:
    model = None
    client = None

    @property
    def started(self) -> bool:
        return self.client is not None

    def startup(self, base_url, api_key, model):
        from ..llm import create_client
        self.model = model
        self.client = create_client(base_url=base_url, api_key=api_key)

    async def shutdown(self):
        self.model = None
        await self.client.close()
        self.client = None

# Global lifespan chat completions client
chat_client = LifespanClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup, create a chat completion client
    logger.info(f"Starting up HuRAG API Server...")

    import os
    base_url = os.getenv(f"{conf.llm.generation}_BASE_URL")
    api_key = os.getenv(f"{conf.llm.generation}_API_KEY")
    model = os.getenv(f"{conf.llm.generation}_MODEL")
    try:
        chat_client.startup(base_url, api_key, model)
        logger.info("Lifespan chat completions client is created.")

        yield

    except Exception as e:
        logger.error(f"Failed to startup HuRAG API Server: {e!r}")
        raise
    finally:
        logger.info("Closing chat completions client...")
        await chat_client.shutdown()
        logger.info("HuRAG API Server shutdown complete.")


app = FastAPI(
    title = "HuRAG-Server",
    description = "HuRAG API Server",
    version = hurag_version,
    openai_tags = [
        {"name": "项目信息", "description": "获取项目相关的一些常用信息"},
        {"name": "大模型", "description": "与HuRAG使用的大模型进行交互"},
        {"name": "知识库", "description": "在HuRAG的知识库中进行检索查询"},
    ],
    lifespan=lifespan,
)

app.include_router(info_router)
# app.include_router(llm_router)
# app.include_router(hurag_router)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon_redirect():
    return Response(status_code=204)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {
        "server": f"HuRAG-Server {hurag_version}",
        "org": conf.app.org_path.split("/")[-1],
    }

def main():
    # change to gunicorn + uvicorn.workers.UvicornWorker in product environment
    import os
    src_dir = os.path.dirname(os.path.abspath(__file__))
    uvicorn.run(
        "hurag.hurag_server.server:app",
        host="0.0.0.0",
        port=5002,
        reload=True,
        reload_dirs=[src_dir],
    )

if __name__ == "__main__":
    main()

