# Giacomino

API for my custom [chatbot](https://www.giacomociro.com).

## Setup

Copy `.env.example` to `.env` and fill in the values.

Install dependencies and run:

```bash
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 5050
```