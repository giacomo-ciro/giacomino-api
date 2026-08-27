API for a custom RAG-based chatbot living on my personal website.

This codebase implements a minimal, simple and efficient FastAPI API that exposes routes to interact with the custom chatbot. Dependencies are managed with `uv` via `pyproject.toml`.

The actual LLM inference is routed through Together.ai.

Documents are embedded via Together's embeddings API and stored in a ChromaDB collection persisted to disk (`chroma_data/`), synced incrementally by content hash so unchanged chunks aren't re-embedded on restart.

## Structure

- `app/main.py` — FastAPI app, CORS, routers, startup
- `app/config.py` — typed settings, read from `.env`
- `app/giacomino.py` — the `Giacomino` class: retrieval (Chroma) + generation (Together chat)
- `app/routes/` — one file per endpoint (`/`, `/status`, `/chat`, `/history`)
- `app/schemas/` — request/response models
- `app/dependencies.py` — `requires_env` / `rate_limit` FastAPI dependencies
- `documents/documents.yaml` — the chatbot's knowledge base (YAML list of text chunks)
- `prompts/system.txt` — the system prompt template
