import pytest
from app.services.document_store import DocumentStore
from app.utils.auth import create_access_token
from tests.conftest import TEST_SECRETS


def _auth_header(client):
    res = client.post("/admin/login", json={"password": "test-password"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_add_and_get_by_id(mock_store: DocumentStore):
    id_ = mock_store.add("hello world", {})
    doc = mock_store.get_by_id(id_)
    assert doc is not None
    assert doc["content"] == "hello world"


def test_update_document(mock_store: DocumentStore):
    id_ = mock_store.add("original", {})
    mock_store.update(id_, "updated", None)
    assert mock_store.get_by_id(id_)["content"] == "updated"


def test_delete_document(mock_store: DocumentStore):
    id_ = mock_store.add("to delete", {})
    mock_store.delete(id_)
    assert mock_store.get_by_id(id_) is None


def test_get_all_returns_added_docs(mock_store: DocumentStore):
    initial = len(mock_store.get_all())
    mock_store.add("doc 1", {})
    mock_store.add("doc 2", {})
    assert len(mock_store.get_all()) == initial + 2


def test_seed_adds_only_new_chunks(mock_store: DocumentStore, tmp_path):
    doc_file = tmp_path / "docs.txt"
    doc_file.write_text("chunk one\n---\nchunk two\n")
    mock_store.seed_from_file(str(doc_file))
    assert len(mock_store.get_all()) == 2

    doc_file.write_text("chunk one\n---\nchunk two\n---\nchunk three\n")
    mock_store.seed_from_file(str(doc_file))
    assert len(mock_store.get_all()) == 3


def test_seed_is_idempotent(mock_store: DocumentStore, tmp_path):
    doc_file = tmp_path / "docs.txt"
    doc_file.write_text("only chunk\n")
    mock_store.seed_from_file(str(doc_file))
    assert len(mock_store.get_all()) == 1
    mock_store.seed_from_file(str(doc_file))
    assert len(mock_store.get_all()) == 1


def test_admin_crud_via_api(client):
    headers = _auth_header(client)

    # Create
    res = client.post("/admin/documents", json={"content": "test doc"}, headers=headers)
    assert res.status_code == 200
    doc_id = res.json()["id"]

    # List
    res = client.get("/admin/documents", headers=headers)
    assert res.status_code == 200
    ids = [d["id"] for d in res.json()]
    assert doc_id in ids

    # Update
    res = client.put(f"/admin/documents/{doc_id}", json={"content": "updated"}, headers=headers)
    assert res.status_code == 200

    # Delete
    res = client.delete(f"/admin/documents/{doc_id}", headers=headers)
    assert res.status_code == 200

    # Verify gone
    res = client.delete(f"/admin/documents/{doc_id}", headers=headers)
    assert res.status_code == 404
