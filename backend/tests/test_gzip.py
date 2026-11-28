"""Gzip shrinks large responses (GET /snapshot is ~9 MB) and must never buffer a stream."""

from starlette.testclient import TestClient

from app.main import app

MCP_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}},
}


def test_large_responses_are_gzipped_for_clients_that_accept_it(client):
    response = client.get("/llms.txt", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert "A2A" in response.text  # the client decodes it transparently


def test_small_responses_and_clients_without_gzip_are_left_alone(client):
    assert "content-encoding" not in client.get("/health", headers={"Accept-Encoding": "gzip"}).headers
    assert "content-encoding" not in client.get("/llms.txt", headers={"Accept-Encoding": "identity"}).headers


def test_mcp_event_stream_is_never_compressed(mock_db):
    from unittest.mock import patch

    with patch("app.main.db", mock_db), TestClient(app) as c:
        response = c.post(
            "/mcp/",
            json=MCP_INIT,
            headers={"Accept": "application/json, text/event-stream", "Accept-Encoding": "gzip"},
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "content-encoding" not in response.headers
