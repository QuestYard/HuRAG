# Copilot Instructions for HuRAG

## Build, Test, and Lint

This project uses `uv` for dependency management and execution.

*   **Install dependencies:**
    ```bash
    uv sync
    ```
*   **Run API Server:**
    ```bash
    uv run hurag-server
    ```
*   **Run WebUI:**
    ```bash
    uv run hurag-webui
    ```
*   **CLI Tools:**
    *   `uv run hurag` (Knowledge Base CLI)
    *   `uv run corpus` (Corpus CLI)
    *   `uv run kgraph` (Knowledge Graph CLI)
*   **Linting/Formatting:**
    *   The project uses `pyright` for static type checking (configured in `pyrightconfig.json`).
    *   Use `uv run pyright` to run type checks.

## High-Level Architecture

HuRAG is a RAG application specialized for legal/regulatory documents with a focus on organizational structure and temporal validity.

*   **Core Services:**
    *   **API Server (`hurag-server`):** FastAPI-based backend providing REST endpoints for RAG retrieval (`/v1/hurag/retrieve`) and chat (`/v1/llm/chat`).
    *   **WebUI (`hurag-webui`):** NiceGUI-based frontend for user interaction.
*   **Data Layer:**
    *   **Relational DB (MariaDB/MySQL):** Stores metadata, corpus, and organizational structure.
    *   **Vector DB (Milvus):** Stores document embeddings.
*   **RAG Engine:**
    *   **TH-GraphRAG:** Uses a temporal and hierarchical knowledge graph.
    *   **Organization Tree:** Users are tied to nodes in an org tree, restricting search scope.
    *   **Document Processing:** Supports PDF, Word, Excel, etc., via `MarkItDown`.
*   **External Dependencies:**
    *   Relies on an external `embedding-service` for embeddings/reranking.
    *   Uses OpenAI-compatible APIs for LLM generation.

## Key Conventions

*   **Configuration:**
    *   **`hurag.yaml`:** Main application config (DB connections, model tags, retrieval params).
    *   **`.env`:** Secrets and environment-specific variables (API keys, model specific URLs).
    *   **Model Mapping:** `hurag.yaml` defines model *tags* (e.g., "DEEPSEEK"), which map to environment variables in `.env` (e.g., `DEEPSEEK_BASE_URL`, `DEEPSEEK_API_KEY`).
*   **Type Hinting:**
    *   Strict type hinting is encouraged to satisfy `pyright`.
    *   Use `TYPE_CHECKING` blocks for imports used only for typing to avoid circular dependencies.
    *   Handle `None` values explicitly, especially from external API responses.
*   **WebUI Pattern:**
    *   **NiceGUI Isolation:** Global events share the same worker. Always check `ui.context.client` in event handlers to ensure data isolation between users.
    *   **Matplotlib:** Can be disabled via `MATPLOTLIB="false"` env var for faster startup.
*   **Database Injection:**
    *   Functions using `@with_rdb` decorator should have `conn` and `cur` arguments typed as optional (`None`) or `Any` to satisfy static analysis, as they are injected at runtime.
