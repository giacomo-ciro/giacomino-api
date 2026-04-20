# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (uv required)
uv sync

# Run dev server (auto-reload)
uvicorn app.main:app --reload --port 8000

# Run production server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run tests
uv run pytest tests/ -v

# Manual test
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "hello"}]}'
```

## Environment

`.env` contains secrets only:

```
TOGETHER_API_KEY=
HISTORY_KEY=
ADMIN_PASSWORD=
JWT_SECRET=
```

Non-secret config (model names, rate limits, paths) lives in `configs/config.yaml`.

## Architecture

**Purpose**: Personal RAG-based chatbot API that answers questions about Giacomo Cirò.

### Request flow

```
POST /chat
  → slowapi rate_limit
  → RAGPipeline.run(PipelineContext)
      → EmbedQueryStep         (extract query from messages)
      → RetrieveDocsStep       (ChromaDB similarity search)
      → BuildPromptStep        (inject context into system.txt template)
      → GenerateResponseStep   (Pydantic AI + Together LLM)
      → PersistHistoryStep     (write to SQLite conversations.db)
  → ChatResponse(text, timestamp)
```

### Directory structure

```
app/
├── main.py             FastAPI app factory, CORS, error handlers, lifespan
├── config.py           Secrets (pydantic-settings .env) + AppConfig (configs/config.yaml)
├── dependencies.py     FastAPI DI: singleton DocumentStore, MyLogger, RAGPipeline, JWT verify
├── routers/
│   ├── chat.py         POST /chat, GET /history
│   ├── status.py       GET /, GET /status
│   └── admin.py        POST /admin/login, CRUD /admin/documents, GET /admin
├── pipeline/
│   ├── base.py         PipelineContext dataclass, PipelineStep Protocol, RAGPipeline
│   └── steps.py        EmbedQueryStep, RetrieveDocsStep, BuildPromptStep,
│                         GenerateResponseStep (Pydantic AI), PersistHistoryStep (aiosqlite)
├── services/
│   └── document_store.py  ChromaDB CRUD + TogetherEmbeddingFunction
├── models/
│   ├── chat.py         ChatRequest, ChatResponse, Message
│   ├── document.py     Document, DocumentCreate, DocumentUpdate
│   └── errors.py       ErrorResponse (error, detail, timestamp, request_id)
├── prompts/
│   └── system.txt      System prompt with {context} and {date} placeholders
├── utils/
│   ├── logger.py       MyLogger
│   ├── auth.py         JWT create/decode (python-jose)
│   └── rate_limit.py   slowapi Limiter instance
└── static/
    └── admin.html      Single-page admin UI (JWT-authenticated, inline CSS+JS)
configs/
└── config.yaml         Non-secret config: model names, rate limits, paths
data/
├── documents.txt       Knowledge base, chunks separated by ---
└── conversations.db    SQLite conversation history (auto-created on startup)
tests/
├── conftest.py         TestClient + mock fixtures (isolated ChromaDB, mocked embeddings)
├── test_auth.py
├── test_chat.py
└── test_documents.py
```

### Key files

- [app/main.py](../app/main.py) — App factory; lifespan seeds ChromaDB and creates SQLite table
- [app/pipeline/steps.py](../app/pipeline/steps.py) — All RAG pipeline steps; adding a step = one list insert in `dependencies.py`
- [app/services/document_store.py](../app/services/document_store.py) — ChromaDB abstraction; `TogetherEmbeddingFunction` ensures embedding consistency
- [configs/config.yaml](../configs/config.yaml) — Tune model, rate limit, paths here
- [app/prompts/system.txt](../app/prompts/system.txt) — System prompt; `{context}` and `{date}` are injected per request

### Vector DB

ChromaDB `PersistentClient` at `./chroma_db` (auto-seeded from `data/documents.txt` on first run if collection is empty). Chunks split by `---`. Custom `TogetherEmbeddingFunction` keeps embedding model consistent between indexing and querying.

### Conversation tracking

SQLite at `data/conversations.db`. Schema: `conversations(id, timestamp, client_ip, user_message, assistant_response, metadata)`. Async writes via `aiosqlite` prevent race conditions.

### Admin UI

JWT-protected single-page app at `/admin`. Login with `ADMIN_PASSWORD` → JWT stored in `sessionStorage` → full CRUD on ChromaDB documents.

## Coding Standard
- Match the style and structure of the existing code inside `app/`.
- Use type hints on all functions.
- Do not use docstrings.
- Write clear, concise comments to explain non-obvious logic. Avoid docstrings; use inline comments.
- Keep code simple, modular, and easy to follow.
- SOLID principles: single responsibility per class, depend on abstractions.
- Organize code into additional Python files and modules as needed.
- Place all test files in the `tests/` directory.
- Update `.claude/CLAUDE.md` to reflect any changes.
- Update `tests/` to reflect any changes. Keep tests minimal, follow the existing structure.
