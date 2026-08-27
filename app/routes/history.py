import logging
import os

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import requires_env
from app.schemas.common import ErrorResponse
from app.schemas.history import HistoryResponse

router = APIRouter(tags=["History"])


@router.get(
    "/history",
    dependencies=[Depends(requires_env)],
    response_model=HistoryResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Environment configuration missing."},
        500: {"model": ErrorResponse, "description": "Failed to retrieve history."},
    },
)
def get_history():
    """
    Returns the chat history in JSON format.
    """
    logger = logging.getLogger("giacomino")
    try:
        if not os.path.exists("dump/saved_messages.jsonl"):
            return {"history": [], "message": "No history file found"}

        with open("dump/saved_messages.jsonl", "r") as file:
            history_data = file.read()

        return {"history": history_data}

    except Exception as e:  # noqa: BLE001 — intentional safety net, never surfaces internals to the caller
        logger.error(f"Error retrieving history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")
