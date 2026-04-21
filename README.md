# Giacomino

API for my custom [chatbot](https://www.giacomociro.com).

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
ADMIN_PASSWORD=
JWT_SECRET=
```

Non-secret config (model names, rate limits, paths) lives in `configs/config.yaml`.