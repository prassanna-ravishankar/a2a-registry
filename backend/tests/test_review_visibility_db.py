"""Hidden-until-approved against a real Postgres: held agents are absent from every public read.

Runs only when TEST_DATABASE_URL points at a disposable database; every migration is applied
to a fresh schema first.
"""

import os
from pathlib import Path

import asyncpg
import pytest

from app.card_classifier import CardVerdict
from app.models import AgentCreate
from app.repositories import AgentRepository

DB_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")

MIGRATIONS = sorted((Path(__file__).parent.parent / "migrations" / "versions").glob("*.sql"))
FLAGGED = CardVerdict(score=0.95, signals={"injection": 0.95}, model="jev-test")
CLEAN = CardVerdict(score=0.02, signals={}, model="jev-test")


class _Db:
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
async def repo():
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    for migration in MIGRATIONS:
        await conn.execute(migration.read_text())
    yield AgentRepository(_Db(conn))
    await conn.close()


def _agent(n: int) -> AgentCreate:
    return AgentCreate(
        protocolVersion="0.3.0",
        name=f"Unique Review Agent {n}",
        description="Searchable reviewtoken description",
        author=f"Author {n}",
        wellKnownURI=f"https://agent{n}.example.com/.well-known/agent.json",
        url=f"https://agent{n}.example.com/a2a",
        version="1.0.0",
        capabilities={"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain"],
        skills=[],
    )


async def _publicly_visible(repo: AgentRepository, agent_id) -> bool:
    by_id = await repo.get_by_id(agent_id) is not None
    listed, _ = await repo.list_agents(limit=100, offset=0)
    searched, _ = await repo.list_agents(search="reviewtoken", limit=100, offset=0)
    views = {by_id, agent_id in {a.id for a in listed}, agent_id in {a.id for a in searched}}
    assert len(views) == 1, "public reads disagree about visibility"
    return views.pop()


async def test_pending_agent_is_never_publicly_visible_until_approved(repo):
    created = await repo.create(_agent(1), review_status="pending")
    await repo.record_card_review(created.id, FLAGGED, "sha-1", "pending", previous="pending")

    assert not await _publicly_visible(repo, created.id)
    assert [a["id"] for a in await repo.list_review_queue()] == [created.id]

    assert await repo.decide_review(created.id, approve=True)
    assert await _publicly_visible(repo, created.id)
    state = await repo.get_review_state(created.id)
    assert state["review_status"] == "approved" and state["review_approved_sha256"] == "sha-1"


async def test_rejected_agent_stays_hidden(repo):
    created = await repo.create(_agent(2), review_status="pending")
    await repo.record_card_review(created.id, FLAGGED, "sha-2", "pending", previous="pending")

    assert await repo.decide_review(created.id, approve=False)
    assert not await _publicly_visible(repo, created.id)
    assert await repo.list_review_queue() == []


async def test_unscored_agent_is_hidden_and_cannot_be_approved_blind(repo):
    created = await repo.create(_agent(3), review_status="unscored")
    await repo.record_card_review(created.id, None, "sha-3", "unscored", previous="unscored")

    assert not await _publicly_visible(repo, created.id)
    assert await repo.list_unscored() == [(created.id, "https://agent3.example.com/.well-known/agent.json")]
    assert not await repo.decide_review(created.id, approve=True)

    await repo.record_card_review(created.id, CLEAN, "sha-3", None, previous="unscored")
    assert await _publicly_visible(repo, created.id)


async def test_flagged_published_agent_stays_visible_until_decided(repo):
    created = await repo.create(_agent(4))
    await repo.record_card_review(created.id, FLAGGED, "sha-4", "flagged", previous=None)

    assert await _publicly_visible(repo, created.id)
    assert [a["review_status"] for a in await repo.list_review_queue()] == ["flagged"]


async def test_review_never_republishes_an_agent_hidden_for_other_reasons(repo):
    created = await repo.create(_agent(5))
    await repo.delete(created.id)  # soft delete / dead-agent auto-hide

    await repo.record_card_review(created.id, CLEAN, "sha-5", None, previous=None)
    assert not await _publicly_visible(repo, created.id)
