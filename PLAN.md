# Plan: Serve the Control Dashboard at API Root

## Context

`docs/dashboard.md` + `docs/dashboard.html` are a spec + static prototype (built via
`tmp-design`) for an admin dashboard: telemetry, log viewer, indexed-chunk browser,
RAG query simulator, `.env` editor, chat history viewer. Goal: serve it at `GET /`
and back it with real endpoints instead of the prototype's mock data.

**Important mismatch**: the spec/prototype were written against what looks like the
*previous* Flask implementation (deleted `app.py`, `giacomino.py`, `utils.py`,
`system.txt`, `requirements.txt`, `documents.txt` in git status) — not the current
FastAPI + Chroma refactor. Concretely, the spec's `.env` schema references
`FLASK_ENV` and `PORT`, neither of which exists in the current
`app/config.py::Settings`. This plan implements the dashboard against the
**current** `Settings` model, not the literal field list in `docs/dashboard.md`.
Flagging this explicitly rather than silently reconciling it — correct me if
`PORT`/`FLASK_ENV` should be reintroduced as real settings.

## Decisions locked in (per discussion)

- **Auth**: nothing app-level. `/`, `/status`, `/documents`, `/retrieve`,
  `/settings`, and `/history` are all protected only by Cloudflare Access at the
  edge (+ service tokens for the website's `/chat` proxy, as already documented in
  `docs/arch.md`).
- **`/settings`**: full read/write/hot-reload capability (GET returns current
  config, POST writes to `.env` on disk, updates `os.environ`, and re-instantiates
  `Giacomino` in place) — scoped to the fields that actually exist in `Settings`.

## Current vs. target endpoint state

| Endpoint | Now | Target |
|---|---|---|
| `GET /` | JSON stub | Serves the dashboard HTML |
| `GET /status` | status/version/timestamp/docs/models | + `uptime_seconds`, `requests_24h`, `logs_dump` |
| `GET /history` | No auth, returns raw JSONL string | Returns parsed `{"sessions": [...]}` |
| `GET /documents` | Missing | New — lists indexed chunks |
| `POST /retrieve` | Missing | New — vector search without generation |
| `GET/POST /settings` | Missing | New — read/write config + hot-reload |
| `POST /chat` | Unchanged | Unchanged |

## Implementation steps

### 1. Reshape `/history` into sessions
- Parse each line of `dump/saved_messages.jsonl` (format: `[{"timestamp": ...}, {"role": "user"/"assistant", "content": ...}, ...]`, per `Giacomino._save_messages_to_disk`).
- For each line, take the timestamp plus the **last** user/assistant message pair in that line (a saved line can contain a full multi-turn transcript sent by the client; we show it as one session card, matching the prototype's one-bubble-pair-per-card UI — not exploding into per-turn cards).
- Return `{"sessions": [{"timestamp", "user", "assistant"}, ...]}`. Missing file → `{"sessions": []}`.

### 2. `/status` additions
- `uptime_seconds`: stamp `app.state.start_time = time.time()` in the `lifespan`, diff in the route.
- `requests_24h`: add a small in-memory timestamp list in `app/dependencies.py` (`record_request()` / `count_requests_last_24h()`, independent of the existing rate-limit store since that one prunes to a 1h window and can't answer a 24h query). Call `record_request()` from the `/chat` handler — that's the traffic that matters here.
- `logs_dump`: add a bounded in-memory ring-buffer `logging.Handler` (e.g. `deque(maxlen=200)`) wired up in `app/logging_config.py`, plus a `get_recent_logs() -> str` accessor. Chosen over tailing `LOG_FILE` because it works even when `LOG_FILE` is unset and needs no file I/O on every status poll.

### 3. `GET /documents`
- New `app/routes/documents.py`. Source of truth: `giacomino.documents` (already the in-memory list synced with Chroma on startup — no need to re-query Chroma).
- Response: `[{"id": <1-based index>, "content": ..., "chars": len(content), "status": "indexed"}]`.

### 4. `POST /retrieve`
- New `app/schemas/retrieve.py`: `RetrieveRequest {query: str, top_k: int | None}`.
- `Giacomino.retrieve_context` gets an optional `top_k` param (currently hardwired to `self.top_k`) so the simulator can override it per-query without mutating instance state.
- Response: `{"query", "top_k", "results": [{"id", "content"}]}` — `id` derived via `self.documents.index(content) + 1` so ids line up with the `/documents` table (fine at this doc-set size; no new indexing structure needed).

### 5. `GET`/`POST /settings`
- New `app/schemas/settings.py`: `SettingsUpdate` mirrors `Settings` with every field optional.
- New `app/routes/settings.py`:
  - `GET`: current settings from `get_settings()`, with `TOGETHER_API_KEY` masked (`tgp_v1_***`-style).
  - `POST`: merge given keys into `.env` on disk (rewrite matching `KEY=` lines, append new ones, leave others untouched), update `os.environ`, `get_settings.cache_clear()`, build a **new** `Giacomino` instance, and only then assign it to `app.state.giacomino` — so an in-flight request never sees a half-constructed instance, and if the new instance fails to build (e.g. bad key), the old one stays live and the endpoint returns `{"status": "error", "message": ...}` instead of taking the app down.
- Fields covered: `TEXT_MODEL_PATH`, `EMB_MODEL_PATH`, `RETRIEVE_TOP_K`, `MAX_CHARS`, `CHAT_REQUESTS_PER_HOUR_LIMIT`, `CHROMA_PERSIST_DIR`, `LOG_FILE`, `TOGETHER_API_KEY`. No `FLASK_ENV`/`PORT` (don't correspond to anything in the current app — port is a `uvicorn`/`gunicorn` bind flag, not app config).

### 6. Serve the dashboard at `/`
- Move `docs/dashboard.html` → `app/static/dashboard.html` (it's a served asset now, not documentation) — `git mv`, then strip prototype-only chrome out of it:
  - Remove the floating `.proto-bar` (mock/live/degraded toggle, `protoApiUrl`/`protoHistoryKey` inputs) and the `MOCK_DOCS` / `rawLogs` / `mockHistory` arrays entirely.
  - Wire every tab to the real, same-origin endpoints unconditionally (no base-URL input needed — dashboard is served by the API itself, so no CORS to configure for it): Overview → `/status` (+ `/documents` count), Logs → `logs_dump` from `/status`, Documents → `/documents`, Query Simulator → `POST /retrieve` (replacing the client-side fuzzy term-matching mock), `.env` tab → `GET/POST /settings`, History → `/history`.
- `app/routes/root.py`: serve the file via `FileResponse`/`HTMLResponse` instead of the current JSON stub.
- `app/main.py`: register the two new routers (`documents`, `settings`); set `app.state.start_time` in `lifespan`.

### 7. Docs reconciliation
- Update `docs/dashboard.md`'s endpoint schemas and route table to match what's actually shipped (drop `FLASK_ENV`/`PORT` fields, reflect real `Settings` fields) — otherwise the spec doc immediately goes stale.

## Verification

No test suite exists in this repo yet, so verification is manual:
1. `uv run uvicorn app.main:app --reload` locally.
2. Load `http://127.0.0.1:8000/` — confirm the dashboard renders and every tab pulls live data (no mock arrays left in the shipped JS).
3. Exercise the Query Simulator against a real query, confirm results match `/retrieve` called directly via `curl`.
4. Submit a small, safe change via the `.env` tab (e.g. `MAX_CHARS`) and confirm: `.env` on disk updated, `/status` reflects the new value, chat still works after the in-place reload.
5. Send a couple of `/chat` messages, confirm they show up in the History tab and `requests_24h` increments.
