from functools import lru_cache
from pathlib import Path

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import AppConfig, Secrets, get_config, get_secrets
from app.pipeline.base import RAGPipeline
from app.pipeline.steps import (
    BuildPromptStep,
    EmbedQueryStep,
    GenerateResponseStep,
    PersistHistoryStep,
    RetrieveDocsStep,
)
from app.services.document_store import DocumentStore
from app.utils.auth import decode_token
from app.utils.logger import MyLogger

_security = HTTPBearer()


@lru_cache(maxsize=1)
def get_document_store() -> DocumentStore:
    secrets = get_secrets()
    config = get_config()
    logger = get_logger()
    store = DocumentStore(secrets, config, logger)
    store.seed_from_file(config.documents_path)
    return store


@lru_cache(maxsize=1)
def get_logger() -> MyLogger:
    config = get_config()
    return MyLogger(name="giacomino-api", log_file=config.log_file)


def get_pipeline(
    secrets: Secrets = Depends(get_secrets),
    config: AppConfig = Depends(get_config),
    store: DocumentStore = Depends(get_document_store),
    logger: MyLogger = Depends(get_logger),
) -> RAGPipeline:
    system_template = Path("app/prompts/system.txt").read_text()
    return RAGPipeline(
        [
            EmbedQueryStep(logger),
            RetrieveDocsStep(store, config, logger),
            BuildPromptStep(system_template, logger),
            GenerateResponseStep(secrets, config, logger),
            PersistHistoryStep(config.conversations_db_path, logger),
        ],
        logger,
    )


def verify_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    secrets: Secrets = Depends(get_secrets),
) -> str:
    return decode_token(credentials.credentials, secrets.JWT_SECRET)
