from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import AppConfig, Secrets, get_config, get_secrets
from app.dependencies import get_document_store, verify_jwt
from app.models.document import Document, DocumentCreate, DocumentUpdate
from app.services.document_store import DocumentStore
from app.utils.auth import create_access_token

router = APIRouter(prefix="/admin")


class AdminLogin(BaseModel):
    password: str


@router.get("")
async def admin_ui() -> FileResponse:
    return FileResponse("app/static/admin.html")


@router.post("/login")
async def login(body: AdminLogin, secrets: Secrets = Depends(get_secrets), config: AppConfig = Depends(get_config)) -> dict:
    if body.password != secrets.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_access_token("admin", secrets.JWT_SECRET, 24)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/documents", dependencies=[Depends(verify_jwt)])
async def list_documents(store: DocumentStore = Depends(get_document_store)) -> list[Document]:
    return [Document(**d) for d in store.get_all()]


@router.post("/documents", dependencies=[Depends(verify_jwt)])
async def create_document(
    body: DocumentCreate,
    store: DocumentStore = Depends(get_document_store),
) -> dict:
    id_ = store.add(body.content, body.metadata)
    return {"id": id_}


@router.put("/documents/{doc_id}", dependencies=[Depends(verify_jwt)])
async def update_document(
    doc_id: str,
    body: DocumentUpdate,
    store: DocumentStore = Depends(get_document_store),
) -> dict:
    if not store.get_by_id(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    store.update(doc_id, body.content, body.metadata)
    return {"updated": doc_id}


@router.delete("/documents/{doc_id}", dependencies=[Depends(verify_jwt)])
async def delete_document(
    doc_id: str,
    store: DocumentStore = Depends(get_document_store),
) -> dict:
    if not store.get_by_id(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    store.delete(doc_id)
    return {"deleted": doc_id}
