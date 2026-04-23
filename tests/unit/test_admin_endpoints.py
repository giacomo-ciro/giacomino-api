import sqlite3

import pytest


def _auth_header(client):
    res = client.post("/admin/login", json={"password": "test-password"})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _seed_conversations(config, rows):
    with sqlite3.connect(config.conversations_db_path) as conn:
        conn.executemany(
            "INSERT INTO conversations (timestamp, client_ip, user_message, assistant_response) VALUES (?,?,?,?)",
            rows,
        )
        conn.commit()


# --- conversations ---

def test_conversations_requires_auth(client):
    res = client.get("/admin/conversations")
    assert res.status_code in (401, 403)


def test_conversations_empty(client):
    headers = _auth_header(client)
    res = client.get("/admin/conversations", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1


def test_conversations_pagination(client, monkeypatch):
    from app.config import get_config
    config = get_config()
    rows = [(f"2026-04-21T10:00:0{i}", "1.2.3.4", f"q{i}", f"a{i}") for i in range(5)]
    _seed_conversations(config, rows)

    headers = _auth_header(client)
    res = client.get("/admin/conversations?page=1&limit=3", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 3
    assert body["total"] == 5
    assert body["limit"] == 3


def test_conversations_filter_by_ip(client):
    from app.config import get_config
    config = get_config()
    rows = [
        ("2026-04-21T11:00:00", "1.1.1.1", "q1", "a1"),
        ("2026-04-21T11:00:01", "2.2.2.2", "q2", "a2"),
    ]
    _seed_conversations(config, rows)

    headers = _auth_header(client)
    res = client.get("/admin/conversations?ip=1.1.1.1", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert all(item["client_ip"] == "1.1.1.1" for item in body["items"])


def test_conversations_filter_by_date(client):
    from app.config import get_config
    config = get_config()
    rows = [
        ("2026-01-01T10:00:00", "1.1.1.1", "old", "old"),
        ("2026-04-21T10:00:00", "1.1.1.1", "new", "new"),
    ]
    _seed_conversations(config, rows)

    headers = _auth_header(client)
    res = client.get("/admin/conversations?date_from=2026-04-01", headers=headers)
    body = res.json()
    assert all(item["timestamp"] >= "2026-04-01" for item in body["items"])


# --- logs ---

def test_logs_requires_auth(client):
    res = client.get("/admin/logs")
    assert res.status_code in (401, 403)


def test_logs_returns_entries(client):
    headers = _auth_header(client)
    res = client.get("/admin/logs", headers=headers)
    assert res.status_code == 200
    body = res.json()
    # Logger emits at least one init message on startup
    assert body["total"] >= 1
    assert "items" in body


def test_logs_filter_by_level(client):
    from app.config import get_config
    config = get_config()
    # Write directly to logs db to ensure an ERROR entry exists
    with sqlite3.connect(config.logs_db_path) as conn:
        conn.execute(
            "INSERT INTO logs (timestamp, level, logger, message) VALUES (?,?,?,?)",
            ("2026-04-21T12:00:00", "ERROR", "giacomino-api", "test error"),
        )
        conn.commit()

    headers = _auth_header(client)
    res = client.get("/admin/logs?level=ERROR", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert all(item["level"] == "ERROR" for item in body["items"])
    assert body["total"] >= 1
