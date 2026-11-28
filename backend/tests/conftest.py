import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from fastapi.testclient import TestClient

# Real-Postgres tests (the `db` fixture) run only when TEST_DATABASE_URL points at a
# disposable database; every migration is applied to a fresh schema first.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
requires_postgres = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set")
MIGRATIONS = sorted((Path(__file__).parent.parent / "migrations" / "versions").glob("*.sql"))

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
    "conformance_errors": None,
    "maintainer_notes": None,
    "icon_url": None,
    "supports_authenticated_extended_card": None,
    "security_requirements": None,
    "security_schemes": None,
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


@pytest.fixture(autouse=True)
def clean_jev_verdict():
    """Registration classifies cards with Jev; default every test to a clean verdict."""
    from app.card_classifier import CardVerdict

    verdict = CardVerdict(score=0.01, signals={}, model="jev-test")
    with patch("app.card_classifier.classify_card", new=AsyncMock(return_value=verdict)) as classify:
        yield classify


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


class _PostgresDb:
    """Minimal stand-in for app.database.Database over one connection."""

    def __init__(self, conn):
        self.conn = conn

    async def execute(self, query, *args):
        return await self.conn.execute(query, *args)

    async def fetch(self, query, *args):
        return await self.conn.fetch(query, *args)

    async def fetchrow(self, query, *args):
        return await self.conn.fetchrow(query, *args)

    async def fetchval(self, query, *args):
        return await self.conn.fetchval(query, *args)


@pytest.fixture
async def db():
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    for migration in MIGRATIONS:
        await conn.execute(migration.read_text())
    yield _PostgresDb(conn)
    await conn.close()
