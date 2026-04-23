import pytest
from fastapi import HTTPException

from app.utils.auth import create_access_token, decode_token


def test_create_and_decode_token():
    token = create_access_token("admin", "secret", 1)
    sub = decode_token(token, "secret")
    assert sub == "admin"


def test_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc:
        decode_token("not-a-valid-token", "secret")
    assert exc.value.status_code == 401


def test_wrong_secret_raises_401():
    token = create_access_token("admin", "secret-a", 1)
    with pytest.raises(HTTPException) as exc:
        decode_token(token, "secret-b")
    assert exc.value.status_code == 401


def test_admin_documents_without_token_returns_4xx(client):
    response = client.get("/admin/documents")
    assert response.status_code in (401, 403)


def test_login_correct_password_returns_token(client):
    response = client.post("/admin/login", json={"password": "test-password"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_returns_401(client):
    response = client.post("/admin/login", json={"password": "wrong"})
    assert response.status_code == 401
