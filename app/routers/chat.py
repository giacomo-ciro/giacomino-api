from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import AppConfig, get_config
from app.dependencies import get_logger, get_pipeline
from app.utils.logger import MyLogger
from app.models.chat import ChatRequest, ChatResponse
from app.pipeline.base import PipelineContext, RAGPipeline
from app.utils.rate_limit import limiter

router = APIRouter()


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{get_config().chat_rate_limit_per_hour}/hour")
async def chat(
    body: ChatRequest,
    request: Request,
    pipeline: RAGPipeline = Depends(get_pipeline),
    config: AppConfig = Depends(get_config),
    logger: MyLogger = Depends(get_logger),
) -> ChatResponse:
    client_ip = _get_client_ip(request)
    total_chars = sum(len(m.content) for m in body.messages)
    logger.info(f"Chat request from {client_ip}: {len(body.messages)} messages, {total_chars} chars")
    if total_chars > config.max_chars:
        logger.warning(f"Chat request from {client_ip} exceeded max_chars ({total_chars} > {config.max_chars})")
        raise HTTPException(
            status_code=400,
            detail="Conversation exceeded the character limit. Please start a new chat to continue.",
        )
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    ctx = PipelineContext(messages=messages, client_ip=client_ip)
    response = await pipeline.run(ctx)
    logger.info(f"Chat response to {client_ip}: {len(response)} chars")
    return ChatResponse(text=response, timestamp=datetime.now().isoformat())
