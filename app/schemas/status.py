from pydantic import BaseModel


class DocsInfo(BaseModel):
    quantity: int
    status: str


class ModelsInfo(BaseModel):
    model_text: str
    model_embeddings: str


class StatusResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    docs: DocsInfo | str
    models: ModelsInfo | str
