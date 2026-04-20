from pydantic import BaseModel


class Document(BaseModel):
    id: str
    content: str
    metadata: dict = {}


class DocumentCreate(BaseModel):
    content: str
    metadata: dict = {}


class DocumentUpdate(BaseModel):
    content: str
    metadata: dict | None = None
