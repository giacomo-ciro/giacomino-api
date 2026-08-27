from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.giacomino import Giacomino
from app.logging_config import setup_logging
from app.routes import chat, history, root, status


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger = setup_logging(settings.LOG_FILE)

    if not Path(".env").exists():
        logger.error("Missing .env")

    try:
        giacomino = Giacomino(
            logger=logger,
            together_api_key=settings.TOGETHER_API_KEY,
            chroma_persist_dir=settings.CHROMA_PERSIST_DIR,
            model_text=settings.TEXT_MODEL_PATH,
            model_embeddings=settings.EMB_MODEL_PATH,
            top_k=settings.RETRIEVE_TOP_K,
        )
        logger.info(
            f"Giacomino model initialized with {giacomino.model_text} and {giacomino.model_embeddings}."
        )
    except Exception as e:  # noqa: BLE001 — intentional: don't let init failure crash the app, degrade to unhealthy instead
        logger.error(f"Failed to initialize Giacomino: {e}")
        giacomino = None

    app.state.giacomino = giacomino
    yield


app = FastAPI(
    title="Giacomino API",
    description="RAG-based chatbot API for giacomociro.com.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.giacomociro.com", "https://giacomociro.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root.router)
app.include_router(status.router)
app.include_router(chat.router)
app.include_router(history.router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse({"error": "Endpoint not found"}, status_code=404)
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse({"error": "Internal server error"}, status_code=500)
