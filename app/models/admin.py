from typing import List

from pydantic import BaseModel


class ConversationItem(BaseModel):
    id: int
    timestamp: str
    client_ip: str
    user_message: str
    assistant_response: str
    metadata: str


class PaginatedConversations(BaseModel):
    items: List[ConversationItem]
    total: int
    page: int
    limit: int


class LogItem(BaseModel):
    id: int
    timestamp: str
    level: str
    logger: str
    message: str


class PaginatedLogs(BaseModel):
    items: List[LogItem]
    total: int
    page: int
    limit: int
