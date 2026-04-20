import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import get_config
from app.dependencies import get_document_store, get_logger
from app.models.errors import ErrorResponse
from app.pipeline.steps import PersistHistoryStep
from app.routers import admin, chat, status
from app.utils.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    logger = get_logger()
    logger.info("Application starting up")
    persist_step = PersistHistoryStep(config.conversations_db_path)
    await persist_step.setup()
    logger.info(f"SQLite conversations DB initialized at '{config.conversations_db_path}'")
    get_document_store()
    logger.info(f"ChromaDB initialized at '{config.chroma_db_path}'")
    logger.info("Application startup complete")
    yield
    logger.info("Application shutting down")


def _error_body(request: Request, status_code: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=error,
            detail=detail,
            timestamp=datetime.now().isoformat(),
            request_id=str(getattr(request.state, "request_id", uuid.uuid4())),
        ).model_dump(),
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Giacomino API", version="2.0.0", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request.state.request_id = uuid.uuid4()
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return _error_body(request, 422, "Validation Error", str(exc.errors()))

    @app.exception_handler(HTTPException)
    async def http_handler(request: Request, exc: HTTPException):
        return _error_body(request, exc.status_code, "HTTP Error", exc.detail)

    @app.exception_handler(Exception)
    async def global_handler(request: Request, exc: Exception):
        return _error_body(request, 500, "Internal Server Error", "An unexpected error occurred")

    app.include_router(status.router)
    app.include_router(chat.router)
    app.include_router(admin.router)
    return app


app = create_app()
