import logging
import traceback
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.dependencies import get_giacomino, rate_limit, requires_env
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import ErrorResponse

router = APIRouter(tags=["Chat"])

_settings = get_settings()


@router.post(
    "/chat",
    dependencies=[
        Depends(requires_env),
        Depends(rate_limit(_settings.CHAT_REQUESTS_PER_HOUR_LIMIT, 1)),
    ],
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Environment missing, empty message, or character limit exceeded."},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded."},
        500: {"model": ErrorResponse, "description": "Internal server error."},
        503: {"model": ErrorResponse, "description": "Model not available."},
    },
)
def chat(body: ChatRequest, giacomino=Depends(get_giacomino)):
    """
    Main chat endpoint for the personal chatbot.
    ```
    response = requests.post(
        url="http://127.0.0.1:5001/chat",
        json={
            "messages": [{
                "role": "user",
                "content": "hello"
            }]
        }
    )
    ```
    """
    if not giacomino:
        raise HTTPException(status_code=503, detail="Model not available")

    messages = [m.model_dump() for m in body.messages]
    if not messages:
        raise HTTPException(status_code=400, detail="Empty message")

    settings = get_settings()
    if sum(len(msg["content"]) for msg in messages) > settings.MAX_CHARS:
        raise HTTPException(
            status_code=400,
            detail="Conversation exceeded the character limit. Please start a new chat to continue.",
        )

    try:
        response = giacomino.generate_response(messages)
    except Exception as e:  # noqa: BLE001 — intentional safety net, never surfaces internals to the caller
        logging.getLogger("giacomino").error(
            f"Error in chat endpoint: {e}\n{traceback.format_exc()}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"text": response, "timestamp": datetime.now(UTC).isoformat()}
