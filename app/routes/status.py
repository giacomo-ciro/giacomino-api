from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.dependencies import get_giacomino, requires_env
from app.schemas.common import ErrorResponse
from app.schemas.status import StatusResponse

router = APIRouter(tags=["General"])


@router.get(
    "/status",
    dependencies=[Depends(requires_env)],
    response_model=StatusResponse,
    responses={400: {"model": ErrorResponse, "description": "Environment configuration missing."}},
)
def status_check(giacomino=Depends(get_giacomino)):
    """
    Status check endpoint.
    """
    return {
        "status": "healthy" if giacomino else "unhealthy",
        "version": giacomino.version if giacomino else "N/A",
        "timestamp": datetime.now(UTC).isoformat(),
        "docs": giacomino.get_available_docs() if giacomino else "N/A",
        "models": {
            "model_text": giacomino.model_text if giacomino else "N/A",
            "model_embeddings": giacomino.model_embeddings if giacomino else "N/A",
        },
    }
