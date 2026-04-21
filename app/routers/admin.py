from typing import Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import AppConfig, Secrets, get_config, get_secrets
from app.dependencies import get_document_store, verify_jwt
from app.models.admin import ConversationItem, LogItem, PaginatedConversations, PaginatedLogs
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


@router.get("/conversations", dependencies=[Depends(verify_jwt)])
async def list_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    ip: Optional[str] = Query(None),
    config: AppConfig = Depends(get_config),
) -> PaginatedConversations:
    conditions, params = [], []
    if date_from:
        conditions.append("timestamp >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("timestamp <= ?")
        params.append(date_to + "T23:59:59")
    if ip:
        conditions.append("client_ip = ?")
        params.append(ip)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit

    async with aiosqlite.connect(config.conversations_db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f"SELECT COUNT(*) as n FROM conversations {where}", params) as cur:
            row = await cur.fetchone()
        total = row["n"] if row else 0
        async with db.execute(
            f"SELECT * FROM conversations {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ) as cur:
            rows = await cur.fetchall()

    items = [ConversationItem(**dict(r)) for r in rows]
    return PaginatedConversations(items=items, total=total, page=page, limit=limit)


@router.get("/logs", dependencies=[Depends(verify_jwt)])
async def list_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    config: AppConfig = Depends(get_config),
) -> PaginatedLogs:
    conditions, params = [], []
    if date_from:
        conditions.append("timestamp >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("timestamp <= ?")
        params.append(date_to + "T23:59:59")
    if level:
        conditions.append("level = ?")
        params.append(level.upper())
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit

    async with aiosqlite.connect(config.logs_db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f"SELECT COUNT(*) as n FROM logs {where}", params) as cur:
            row = await cur.fetchone()
        total = row["n"] if row else 0
        async with db.execute(
            f"SELECT * FROM logs {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ) as cur:
            rows = await cur.fetchall()

    items = [LogItem(**dict(r)) for r in rows]
    return PaginatedLogs(items=items, total=total, page=page, limit=limit)
