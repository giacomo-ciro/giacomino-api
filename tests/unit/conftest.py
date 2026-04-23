import pytest
from fastapi.testclient import TestClient

from app.config import AppConfig, get_config, get_secrets
from app.dependencies import get_document_store, get_logger
from app.services.document_store import DocumentStore, TogetherEmbeddingFunction
from tests.conftest import TEST_SECRETS, _fake_embed


@pytest.fixture
def mock_store(tmp_path, monkeypatch):
    monkeypatch.setattr(TogetherEmbeddingFunction, "__call__", _fake_embed)
    config = AppConfig(
        chat_model="test-model",
        embedding_model="test-emb-model",
        retrieve_top_k=3,
        max_chars=2048,
        chat_rate_limit_per_hour=100,
        port=8000,
        logs_db_path=str(tmp_path / "logs.db"),
        chroma_db_path=str(tmp_path / "chroma"),
        documents_path="data/documents.txt",
        conversations_db_path=str(tmp_path / "conversations.db"),
        environment="test",
    )
    return DocumentStore(TEST_SECRETS, config)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(TogetherEmbeddingFunction, "__call__", _fake_embed)

    test_config = AppConfig(
        chat_model="test-model",
        embedding_model="test-emb-model",
        retrieve_top_k=3,
        max_chars=2048,
        chat_rate_limit_per_hour=100,
        port=8000,
        logs_db_path=str(tmp_path / "logs.db"),
        chroma_db_path=str(tmp_path / "chroma"),
        documents_path="data/documents.txt",
        conversations_db_path=str(tmp_path / "conversations.db"),
        environment="test",
    )

    monkeypatch.setattr("app.config._secrets", TEST_SECRETS)
    monkeypatch.setattr("app.config._config", test_config)

    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_secrets] = lambda: TEST_SECRETS
    app.dependency_overrides[get_config] = lambda: test_config

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
