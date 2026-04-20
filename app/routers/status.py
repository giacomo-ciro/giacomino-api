from datetime import datetime

from fastapi import APIRouter, Depends

from app.dependencies import get_logger
from app.utils.logger import MyLogger

router = APIRouter()


@router.get("/")
async def root() -> dict:
    return {"message": "Giacomo Ciro's Personal Chatbot API", "version": "2.0.0"}


@router.get("/status")
async def status_check(logger: MyLogger = Depends(get_logger)) -> dict:
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "logger": logger.get_stats(),
    }
