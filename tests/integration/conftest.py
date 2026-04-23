import pytest
from fastapi.testclient import TestClient

from app.config import AppConfig, get_config, get_secrets, load_config, Secrets
from app.dependencies import get_document_store, get_logger


@pytest.fixture
def integration_docs(tmp_path):
    f = tmp_path / "documents.txt"
    f.write_text(
        "Giacomo Ciro is an AI Master student at Bocconi.\n"
        "---\n"
        "He co-founded BSML, the Bocconi Students for Machine Learning club.\n"
        "---\n"
        "He is a researcher at BIDSA working on ML applied to Biology.\n"
    )
    return str(f)


@pytest.fixture
def integration_client(tmp_path, monkeypatch, integration_docs):
    real_secrets = Secrets()
    base_config = load_config()

    test_config = AppConfig(
        chat_model=base_config.chat_model,
        embedding_model=base_config.embedding_model,
        retrieve_top_k=base_config.retrieve_top_k,
        max_chars=base_config.max_chars,
        chat_rate_limit_per_hour=100,
        port=8000,
        logs_db_path=str(tmp_path / "logs.db"),
        chroma_db_path=str(tmp_path / "chroma"),
        documents_path=integration_docs,
        conversations_db_path=str(tmp_path / "conversations.db"),
        environment="test",
    )

    monkeypatch.setattr("app.config._secrets", real_secrets)
    monkeypatch.setattr("app.config._config", test_config)

    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_secrets] = lambda: real_secrets
    app.dependency_overrides[get_config] = lambda: test_config

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
