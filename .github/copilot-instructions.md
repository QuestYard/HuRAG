# Copilot Instructions for HuRAG

## Project Overview

HuRAG is a Temporal-Hierarchical GraphRAG (TH-GraphRAG) application designed for legal/regulatory documents. It features a dual-service architecture:
-   **API Server (`hurag-server`):** FastAPI-based backend for RAG retrieval and LLM interaction.
-   **WebUI (`hurag-webui`):** NiceGUI-based frontend for user interaction.

## Build and Run

This project uses `uv` for dependency management and execution.

*   **Install dependencies:**
    ```bash
    uv sync
    ```
*   **Run Services:**
    *   **API Server:** `uv run hurag-server` (Host/Port configured in `hurag.yaml` -> `api`)
    *   **WebUI:** `uv run hurag-webui`
*   **CLI Tools:**
    *   **Knowledge Base Management:** `uv run hurag` (Subcommands: `init`, `info`, `list`, `store`)
    *   **Corpus Management:** `uv run corpus`
    *   **Knowledge Graph:** `uv run kgraph`
*   **Linting:**
    *   Run static type checks: `uv run pyright`

## Architecture & Data Access

### Data Support System (DSS)
The `src/hurag/dss` module handles all data access. **Do not access databases directly; use the provided wrappers.**

*   **Relational (`dss.rss`):** Wraps `aiomysql` for MariaDB.
    *   **Injection:** Use the `@with_rdb` decorator to inject `connection` and `cursor`.
    *   **Usage:**
        ```python
        @with_rdb
        async def my_func(conn, cur):
            await cur.execute("SELECT * FROM ...")
        ```
*   **Vector (`dss.vss`):** Wraps `pymilvus` for Milvus.
    *   **Injection:** Use the `@with_vdb` decorator to inject the `client`.
    *   **Usage:**
        ```python
        @with_vdb(client_arg_name="cli")
        async def my_func(cli):
            await cli.search(...)
        ```
*   **Graph (`dss.gss`):** Orchestrates hybrid graph storage (Entities/Relations in MariaDB, Embeddings in Milvus).

### Knowledge Base Manager (`kbman`)
High-level logic for managing the knowledge base resides in `src/hurag/kbman`. Use this module for operations like document deletion, metadata updates, or statistics.

### Business Logic Layers
*   **Document Ingestion (`knowledge_base.py`):** Handles document indexing and vectorization logic (used by `hurag store`).
*   **Graph Logic (`knowledge_graph.py`):** Contains algorithms for entity extraction, normalization, and community detection (Leiden).

## Configuration

*   **`hurag.yaml`:** Main application configuration (DB connections, retrieval parameters, model tags).
*   **`.env`:** Environment variables for secrets and model-specific configs.
    *   **Model Mapping:** `hurag.yaml` defines model *tags* (e.g., `generation: DEEPSEEK`). The code looks up environment variables based on these tags (e.g., `DEEPSEEK_BASE_URL`, `DEEPSEEK_API_KEY`).

## Coding Conventions

*   **Async/Await:** All Database and IO operations are asynchronous. Ensure new functions utilizing `dss` are `async`.
*   **Type Hinting:** Strict type hinting is required to satisfy `pyright`.
    *   Use `TYPE_CHECKING` blocks for circular imports.
    *   Explicitly handle `None` types.
*   **WebUI Isolation:** NiceGUI events share the same worker. Always check `ui.context.client` in event handlers to ensure data isolation between users.
*   **Logging:** Use the project's logger (`from .. import logger`).
