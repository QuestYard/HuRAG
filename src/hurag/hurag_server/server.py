import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
from contextlib import asynccontextmanager

from .. import logger, conf, __version__ as hurag_version

from .api.v1.messages import router as info_router
from .api.v1.llm import router as llm_router
from .api.v1.hurag import router as hurag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app
    try:
        logger.info("HuRAG API Server startup completed.")

        yield

    except Exception as e:
        logger.error(f"HuRAG API Server error: {e!r}")
        raise
    finally:
        from ..dss import rss, vss

        logger.info("Closing MySQL/MariaDB connection pool...")
        await rss.close_pool()
        logger.info("Closing Milvus clients...")
        await vss.close_client()
        from ..llm import close_oa_client

        logger.info("Closing LLM clients...")
        await close_oa_client()
        logger.info("HuRAG API Server shutdown completed.")


app = FastAPI(
    title="HuRAG-Server",
    description="HuRAG API Server",
    version=hurag_version,
    openai_tags=[
        {"name": "项目信息", "description": "获取项目相关的一些常用信息"},
        {"name": "大模型", "description": "与HuRAG使用的大模型进行交互"},
        {"name": "知识库", "description": "在HuRAG的知识库中进行检索查询"},
    ],
    lifespan=lifespan,
)

app.include_router(info_router)
app.include_router(llm_router)
app.include_router(hurag_router)


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
        host=conf.api.host,
        port=conf.api.port,
        reload=True,
        reload_dirs=[src_dir],
    )


if __name__ == "__main__":
    main()
