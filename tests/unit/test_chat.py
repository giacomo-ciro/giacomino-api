from unittest.mock import AsyncMock, patch


def test_chat_returns_200(client):
    with patch("app.pipeline.steps.GenerateResponseStep.execute", new_callable=AsyncMock) as mock_exec:
        async def _side(ctx):
            ctx.response = "Hello from Giacomino!"
            return ctx
        mock_exec.side_effect = _side
        response = client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200
    body = response.json()
    assert "text" in body
    assert "timestamp" in body


def test_chat_response_has_content(client):
    with patch("app.pipeline.steps.GenerateResponseStep.execute", new_callable=AsyncMock) as mock_exec:
        async def _side(ctx):
            ctx.response = "I am Giacomino"
            return ctx
        mock_exec.side_effect = _side
        response = client.post("/chat", json={"messages": [{"role": "user", "content": "who are you?"}]})
    assert response.json()["text"] == "I am Giacomino"


def test_chat_validates_max_chars(client):
    long_msg = "x" * 3000
    response = client.post("/chat", json={"messages": [{"role": "user", "content": long_msg}]})
    assert response.status_code == 400


def test_chat_requires_messages(client):
    response = client.post("/chat", json={})
    assert response.status_code == 422


def test_status_endpoint(client):
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
