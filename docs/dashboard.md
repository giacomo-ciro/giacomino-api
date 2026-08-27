# Control Dashboard Specification & Integration Guide

This document outlines the architecture, UI specification, and backend API contracts for the **Giacomino API Control Dashboard** (`docs/dashboard.html`).

---

## 1. Overview & Architectural Goals

The dashboard provides an admin control panel to monitor API telemetry, view server logs, test knowledge retrieval, inspect indexed documents, manage `.env` configuration, and inspect user chat histories.

### Key Tenets
- **Minimalist Aesthetic**: Direct, unadorned typography and layout aligned with the design tokens of [`giacomo-ciro.github.io`](https://giacomo-ciro.github.io) (`Inter`, `EB Garamond`, `#f4f4f4` background, `#1c1c1c` headings).
- **Zero-Distraction UI**: Stripped of redundant section titles, duplicate headers, and verbose card subtitles.
- **Zero-Reload State Updates**: Live interaction with API endpoints directly from the browser.
- **Cloudflare Access Compatibility**: Built to sit behind Cloudflare Access while allowing the public chatbot endpoint (`POST /chat`) to remain open for portfolio website visitors.

---

## 2. Route Layout & Exposure Strategy

```
                          ┌──────────────────────────┐
                          │   Cloudflare Access      │
                          │   Authentication Wall    │
                          └─────────────┬────────────┘
                                        │
           ┌────────────────────────────┴────────────────────────────┐
           │                                                         │
   [ Protected Paths ]                                       [ Public / Bypassed ]
   ├── GET  /               (dashboard.html)                 └── POST /chat  (Inference)
   ├── GET  /docs           (FastAPI Swagger)
   ├── GET  /status         (Health & Telemetry)
   ├── GET  /history        (Chat Sessions)
   ├── GET  /documents      (Vector Chunks)
   ├── POST /retrieve       (Query Simulator)
   └── POST /settings       (.env Mutation & Reload)
```

- **Dashboard Origin**: Exposed at `GET /` as an `HTMLResponse` serving [`docs/dashboard.html`](file:///Users/gciro/repos/giacomino-api/docs/dashboard.html).
- **FastAPI Interactive Docs**: Accessible at `GET /docs`.
- **Chat Endpoint**: `POST /chat` is bypassed from Cloudflare Access to allow website visitor queries.

---

## 3. Backend Route Status & Requirements

| Endpoint | Method | Current Codebase Status | Action Required |
|---|---|---|---|
| `/` | `GET` | ⚠️ Returns JSON stub (`app.py:43`) | Serve `docs/dashboard.html` via `HTMLResponse` |
| `/status` | `GET` | 🟢 Available (`app.py:55`) | Add `requests_24h` metric to payload |
| `/history` | `GET` | 🟢 Available (`app.py:123`) | Return parsed JSON array of sessions |
| `/documents` | `GET` | 🔴 Missing | Expose current vector index document chunks |
| `/retrieve` | `POST` | 🔴 Missing | Expose vector similarity search without LLM generation |
| `/settings` | `GET` / `POST` | 🔴 Missing | Read `.env` / Write to disk & reload models in memory |

---

## 4. API Endpoints Specification

### 4.1. Health & Telemetry — `GET /status`
Returns server health, uptime, active model identifiers, 24-hour request counts, and recent log dumps.

**Response Schema:**
```json
{
  "status": "healthy",
  "timestamp": "2026-08-27T19:50:00",
  "uptime_seconds": 412940,
  "requests_24h": 128,
  "models": {
    "model_text": "meta-llama/Llama-3.2-3B-Instruct-Turbo",
    "model_embeddings": "BAAI/bge-large-en-v1.5"
  },
  "docs": {
    "quantity": 14,
    "status": "available"
  },
  "logs_dump": "[2026-08-27 19:28:10] [INFO] [MyLogger] Starting app..."
}
```

---

### 4.2. Indexed Knowledge Chunks — `GET /documents`
Returns all chunks currently stored in the vector database (ChromaDB / FAISS).

**Response Schema:**
```json
[
  {
    "id": 1,
    "content": "Giacomo is 22 years old. Giacomo full name is Giacomo Cirò...",
    "chars": 284,
    "status": "indexed"
  }
]
```

---

### 4.3. RAG Query Simulator — `POST /retrieve`
Performs vector similarity search against the index and returns the top $K$ matching chunks without running LLM generation.

**Request Schema:**
```json
{
  "query": "Where did Giacomo work during Formula 1?",
  "top_k": 3
}
```

**Response Schema:**
```json
{
  "query": "Where did Giacomo work during Formula 1?",
  "top_k": 3,
  "results": [
    {
      "id": 10,
      "content": "Giacomo works in access control for Formula 1 Paddock Club events..."
    }
  ]
}
```

---

### 4.4. Environment Settings — `GET /settings` & `POST /settings`
Reads and writes the `.env` configuration.

#### `GET /settings`
**Response Schema:**
```json
{
  "TEXT_MODEL_PATH": "meta-llama/Llama-3.2-3B-Instruct-Turbo",
  "EMB_MODEL_PATH": "BAAI/bge-large-en-v1.5",
  "RETRIEVE_TOP_K": 10,
  "MAX_CHARS": 2048,
  "CHAT_REQUESTS_PER_HOUR_LIMIT": 10,
  "FLASK_ENV": "production",
  "PORT": 5001,
  "LOG_FILE": "logs.txt",
  "TOGETHER_API_KEY": "tgp_v1_***"
}
```

#### `POST /settings`
**Request Schema:** Full dictionary of keys to write.

**Critical Backend Execution:**
1. Atomic write of key-value pairs to `.env` on disk.
2. Update `os.environ`.
3. In-memory reload of `Giacomino` (re-instantiate LLM client, vector index, and embeddings pipeline).

**Response Schema:**
```json
{
  "status": "ok",
  "message": "Configuration saved and runtime models reloaded successfully."
}
```

---

### 4.5. Chat Session History — `GET /history`
Returns message pairs recorded in `saved_messages.jsonl`.

**Response Schema:**
```json
{
  "sessions": [
    {
      "timestamp": "2026-08-27 19:29:04",
      "user": "Hi! Where does Giacomo study?",
      "assistant": "Ciao! Giacomo is currently pursuing an MSc in AI at Bocconi..."
    }
  ]
}
```

---

## 5. UI Features & Layout

1. **Header**: Clean brand title `Giacomino API`, live status pill (`Online (Healthy)` / `Degraded`), and manual refresh button.
2. **Overview & Health Tab**:
   - 4 metric cards: **System Health** (with live `Uptime`), **Port**, **Requests (24h)**, **Indexed Documents**.
   - Minimal 2-row table for active **Text Generation** and **Embeddings** models.
   - **Query Simulator**: Instant query test bar with customizable `Top K` parameter selector.
3. **API Logs Tab**:
   - Real-time terminal log viewer with level filtering (`ALL`, `INFO`, `WARNING`, `ERROR`), search filter, and toggleable auto-scrolling.
4. **Indexed Documents Tab**:
   - Live searchable table of all indexed chunks with character counts and index indices.
5. **.env Tab**:
   - Pure 2-column grid covering all 10 environment configuration keys with password show/hide toggles and Save/Discard actions.
6. **Chat History Tab**:
   - Searchable bubble viewer of recorded conversations with one-click JSONL export.
