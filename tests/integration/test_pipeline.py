import sqlite3

from app.config import AppConfig, get_config, load_config, Secrets
from app.services.document_store import DocumentStore


def test_seed_and_query_chromadb(tmp_path):
    """DocumentStore seeded from a temp .txt file stores and retrieves docs via real ChromaDB embeddings."""
    real_secrets = Secrets()
    base_config = load_config()

    doc_file = tmp_path / "docs.txt"
    doc_file.write_text(
        "Giacomo Ciro is an AI Master student at Bocconi.\n"
        "---\n"
        "He co-founded BSML.\n"
        "---\n"
        "He researches ML applied to Biology at BIDSA.\n"
    )

    config = AppConfig(
        chat_model=base_config.chat_model,
        embedding_model=base_config.embedding_model,
        retrieve_top_k=3,
        max_chars=base_config.max_chars,
        chat_rate_limit_per_hour=100,
        port=8000,
        logs_db_path=str(tmp_path / "logs.db"),
        chroma_db_path=str(tmp_path / "chroma"),
        documents_path=str(doc_file),
        conversations_db_path=str(tmp_path / "conversations.db"),
        environment="test",
    )
    store = DocumentStore(real_secrets, config)
    store.seed_from_file(str(doc_file))

    docs = store.get_all()
    assert len(docs) == 3
    contents = {d["content"] for d in docs}
    assert "Giacomo Ciro is an AI Master student at Bocconi." in contents

    results = store.query("Bocconi", 2)
    assert len(results) >= 1


def test_full_pipeline_persists_conversation(integration_client):
    """POST /chat runs the full pipeline end-to-end with real embeddings and LLM."""
    response = integration_client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Who is Giacomo?"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["text"], str) and len(body["text"]) > 0
    assert "timestamp" in body

    config = get_config()
    with sqlite3.connect(config.conversations_db_path) as conn:
        rows = conn.execute(
            "SELECT user_message, assistant_response FROM conversations"
        ).fetchall()

    assert len(rows) >= 1
    assert any(r[0] == "Who is Giacomo?" for r in rows)
    assert any(len(r[1]) > 0 for r in rows)
