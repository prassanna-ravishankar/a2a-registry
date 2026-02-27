import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


MOCK_AGENT_ROW = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "hidden": False,
    "flag_count": 0,
    "protocol_version": "0.3.0",
    "name": "Test Agent",
    "description": "A test agent for testing",
    "author": "Test Author",
    "well_known_uri": "https://example.com/.well-known/agent.json",
    "url": "https://example.com/a2a",
    "version": "1.0.0",
    "provider": None,
    "documentation_url": None,
    "capabilities": '{"streaming": false, "pushNotifications": false, "stateTransitionHistory": false, "extendedAgentCard": false}',
    "default_input_modes": '["text/plain"]',
    "default_output_modes": '["text/plain"]',
    "skills": '[]',
    "conformance": None,
    "uptime_percentage": 100.0,
    "avg_response_time_ms": 50,
    "last_health_check": "2024-01-01T00:00:00",
    "is_healthy": True,
}

MOCK_AGENT_CARD = {
    "protocolVersion": "0.3.0",
    "name": "Test Agent",
    "description": "A test agent for testing",
    "url": "https://example.com/a2a",
    "version": "1.0.0",
    "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "skills": [],
}


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()
    db.fetchrow = AsyncMock(return_value=MOCK_AGENT_ROW)
    db.fetchval = AsyncMock(return_value=1)
    db.fetch = AsyncMock(return_value=[MOCK_AGENT_ROW])
    db.execute = AsyncMock(return_value="UPDATE 1")
    return db


@pytest.fixture
def client(mock_db):
    # Patch the db object that main.py imported at module load time
    with patch("app.main.db", mock_db):
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
