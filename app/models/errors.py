from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: str
    request_id: str
