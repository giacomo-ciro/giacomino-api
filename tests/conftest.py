import pytest
from fastapi.testclient import TestClient

from app.config import AppConfig, Secrets, get_config, get_secrets
from app.dependencies import get_document_store, get_logger
from app.services.document_store import DocumentStore, TogetherEmbeddingFunction

TEST_SECRETS = Secrets(
    TOGETHER_API_KEY="test-key",
    JWT_SECRET="test-jwt-secret",
    ADMIN_PASSWORD="test-password",
    HISTORY_KEY="test-history-key",
)


def _fake_embed(self, input):
    return [[0.1] * 1024 for _ in input]


@pytest.fixture(autouse=True)
def clear_lru_caches():
    get_document_store.cache_clear()
    get_logger.cache_clear()
    yield
    get_document_store.cache_clear()
    get_logger.cache_clear()


@pytest.fixture
def mock_store(tmp_path, monkeypatch):
    monkeypatch.setattr(TogetherEmbeddingFunction, "__call__", _fake_embed)
    config = AppConfig(
        chat_model="test-model",
        embedding_model="test-emb-model",
        retrieve_top_k=3,
        max_chars=2048,
        chat_rate_limit=100,
        port=8000,
        log_file="/tmp/test-logs.txt",
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
        chat_rate_limit=100,
        port=8000,
        log_file="/tmp/test-logs.txt",
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
