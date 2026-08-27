from typing import Any

from pydantic import BaseModel


class HistoryResponse(BaseModel):
    history: str | list[Any]
    message: str | None = None
