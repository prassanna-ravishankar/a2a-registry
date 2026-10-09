"""Hidden-until-approved against a real Postgres: held agents are absent from every public read.

Runs only when TEST_DATABASE_URL points at a disposable database; every migration is applied
to a fresh schema first.
"""

import os
from pathlib import Path

import asyncpg
import pytest

from app.card_classifier import CardVerdict, ReviewWrite
from app.models import AgentCreate
from app.repositories import AgentRepository, StatsRepository

DB_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")

MIGRATIONS = sorted((Path(__file__).parent.parent / "migrations" / "versions").glob("*.sql"))
FLAGGED = CardVerdict(score=0.95, signals={"injection": 0.95}, model="jev-test")
CLEAN = CardVerdict(score=0.02, signals={}, model="jev-test")


def _review(verdict, sha, status, expect_revision=0):
    return ReviewWrite(verdict=verdict, sha=sha, status=status, expect_revision=expect_revision)


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
async def db():
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    for migration in MIGRATIONS:
        await conn.execute(migration.read_text())
    yield _Db(conn)
    await conn.close()


@pytest.fixture
def repo(db):
    return AgentRepository(db)


def _agent(n: int, **overrides) -> AgentCreate:
    fields = dict(
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
        skills=[{"id": f"reviewskill{n}", "name": "s", "description": "d", "tags": ["t"]}],
    )
    return AgentCreate(**{**fields, **overrides})


async def _publicly_visible(db, repo: AgentRepository, agent_id) -> bool:
    """Visibility through get, list, search and stats, which must all agree."""
    by_id = await repo.get_by_id(agent_id) is not None
    listed, total = await repo.list_agents(limit=100, offset=0)
    searched, _ = await repo.list_agents(search="reviewtoken", limit=100, offset=0)
    stats = await StatsRepository(db).get_registry_stats()
    name = await db.fetchval("SELECT name FROM agents WHERE id = $1", agent_id)
    skill = f"reviewskill{name.split()[-1]}"
    views = {
        by_id,
        agent_id in {a.id for a in listed},
        agent_id in {a.id for a in searched},
        any(s["id"] == skill for s in stats.trending_skills),
    }
    assert len(views) == 1, f"public reads disagree about visibility: {views}"
    assert stats.total_agents == total
    return views.pop()


async def test_pending_agent_is_absent_from_every_public_read_until_approved(db, repo):
    created = await repo.create(_agent(1), review=_review(FLAGGED, "sha-1", "pending"))

    assert not await _publicly_visible(db, repo, created.id)
    queue = await repo.list_review_queue()
    assert [(a["id"], a["jev_card_sha256"]) for a in queue] == [(created.id, "sha-1")]

    assert not await repo.decide_review(created.id, approve=True, card_sha256="some-other-content")
    assert await repo.decide_review(created.id, approve=True, card_sha256="sha-1")
    assert await _publicly_visible(db, repo, created.id)


async def test_rejected_agent_stays_hidden(db, repo):
    created = await repo.create(_agent(2), review=_review(FLAGGED, "sha-2", "pending"))

    assert await repo.decide_review(created.id, approve=False, card_sha256="sha-2")
    assert not await _publicly_visible(db, repo, created.id)
    assert await repo.list_review_queue() == []


async def test_unscored_agent_is_held_cannot_be_approved_and_is_released_once_scored(db, repo):
    created = await repo.create(_agent(3), review=_review(None, "sha-3", "unscored"))

    assert not await _publicly_visible(db, repo, created.id)
    assert not await repo.decide_review(created.id, approve=True, card_sha256="sha-3")

    released = await repo.update_card_metadata(created.id, {}, review=_review(CLEAN, "sha-3", None))
    assert released and await _publicly_visible(db, repo, created.id)


async def test_flagged_published_agent_stays_visible_until_decided(db, repo):
    created = await repo.create(_agent(4))
    await repo.update_card_metadata(created.id, {}, review=_review(FLAGGED, "sha-4", "flagged"))

    assert await _publicly_visible(db, repo, created.id)
    assert [a["review_status"] for a in await repo.list_review_queue()] == ["flagged"]


async def test_moderation_never_revives_a_deleted_agent(db, repo):
    flagged = await repo.create(_agent(5))
    await repo.update_card_metadata(flagged.id, {}, review=_review(FLAGGED, "sha-5", "flagged"))
    unscored = await repo.create(_agent(6), review=_review(None, "sha-6", "unscored"))
    await repo.delete(flagged.id)
    await repo.delete(unscored.id)

    await repo.decide_review(flagged.id, approve=True, card_sha256="sha-5")
    await repo.update_card_metadata(unscored.id, {}, review=_review(CLEAN, "sha-6", None, expect_revision=1))

    assert not await _publicly_visible(db, repo, flagged.id)
    assert not await _publicly_visible(db, repo, unscored.id)


async def test_stale_classification_cannot_overwrite_an_admin_rejection(db, repo):
    created = await repo.create(_agent(7), review=_review(FLAGGED, "sha-7", "pending"))
    stale = _review(CLEAN, "sha-7b", None, expect_revision=0)

    assert await repo.decide_review(created.id, approve=False, card_sha256="sha-7")
    assert not await repo.update_card_metadata(created.id, {"name": "Swapped"}, review=stale)

    state = await repo.get_review_state(created.id)
    assert state["review_status"] == "rejected"
    row = await db.fetchrow("SELECT name, hidden FROM agents WHERE id = $1", created.id)
    assert row["name"] == "Unique Review Agent 7" and row["hidden"] is False


async def test_failed_classification_writes_no_metadata(db, repo):
    created = await repo.create(_agent(8), review=_review(CLEAN, "sha-8", None))

    written = await repo.update_card_metadata(
        created.id, {"description": "changed and unscored"}, review=_review(None, "sha-8b", "unscored"),
    )

    assert written
    row = await db.fetchrow("SELECT description, review_status, jev_card_sha256 FROM agents WHERE id = $1", created.id)
    assert row["description"] == "Searchable reviewtoken description"
    assert (row["review_status"], row["jev_card_sha256"]) == ("unscored", "sha-8")
    assert not await _publicly_visible(db, repo, created.id)


async def test_full_update_is_refused_when_review_state_moved(db, repo):
    created = await repo.create(_agent(9), review=_review(CLEAN, "sha-9", None))
    stale = _review(CLEAN, "sha-9b", None, expect_revision=41)

    assert await repo.update(created.id, _agent(9, name="Changed"), review=stale) is None
    assert (await repo.get_by_id(created.id)).name == "Unique Review Agent 9"


async def test_worker_never_pairs_a_stale_record_with_fresh_review_state(db, repo):
    """Codex re-review #2: the worker holds clean A from the start of the cycle while a
    concurrent PUT stores malicious B as pending. The worker must diff and classify the
    fresh snapshot, so what it publishes is exactly what it scored, never B."""
    from unittest.mock import AsyncMock, patch

    import worker

    clean_a = _agent(10, description="clean A reviewtoken")
    created = await repo.create(clean_a, review=_review(CLEAN, "sha-a", None))
    stale_a = await repo.get_by_id(created.id)

    malicious_b = _agent(10, description="malicious B reviewtoken")
    assert await repo.update(created.id, malicious_b, review=_review(FLAGGED, "sha-b", "pending")) is not None
    assert not await _publicly_visible(db, repo, created.id)

    card_a = clean_a.model_dump(mode="json")
    with patch("app.card_classifier.classify_card", new=AsyncMock(return_value=CLEAN)) as classify:
        await worker.refresh_agent_metadata(stale_a, card_a, repo, conformance_errors=[], classify=True)

    scored = classify.await_args.args[0]["record"]["description"]
    row = await db.fetchrow("SELECT description, review_status FROM agents WHERE id = $1", created.id)
    assert scored == row["description"] == "clean A reviewtoken"
    if await _publicly_visible(db, repo, created.id):
        assert (await repo.get_by_id(created.id)).description == "clean A reviewtoken"


async def test_stale_snapshot_write_is_refused_after_a_concurrent_put(db, repo):
    created = await repo.create(_agent(11), review=_review(CLEAN, "sha-11", None))
    worker_review = _review(CLEAN, "sha-11w", None, expect_revision=0)

    assert await repo.update(created.id, _agent(11, name="Put Wins"), review=_review(FLAGGED, "sha-p", "pending"))
    assert not await repo.update_card_metadata(created.id, {"name": "Worker Overwrite"}, review=worker_review)
    assert await db.fetchval("SELECT name FROM agents WHERE id = $1", created.id) == "Put Wins"


async def test_category_is_stored_with_the_review_counted_and_filterable(db, repo):
    categorised = CardVerdict(
        score=0.02, signals={}, model="jev-test",
        category="payments", category_secondary="crypto-web3", category_confidence=0.7,
    )
    public = await repo.create(_agent(12), review=_review(categorised, "sha-12", None))
    held = await repo.create(_agent(13), review=_review(categorised, "sha-13", "pending"))

    assert (await repo.get_by_id(public.id)).category == "payments"
    # Secondary counts too, matching the filter; the held agent is not counted.
    assert await repo.count_by_category() == {"payments": 1, "crypto-web3": 1}
    by_primary, _ = await repo.list_agents(category="payments", limit=10, offset=0)
    by_secondary, _ = await repo.list_agents(category="crypto-web3", limit=10, offset=0)
    assert [a.id for a in by_primary] == [a.id for a in by_secondary] == [public.id]
    assert held.id not in {a.id for a in by_primary}

    failed = _review(None, "sha-12b", "unscored", expect_revision=0)
    await repo.update_card_metadata(public.id, {}, review=failed)
    row = await db.fetchrow("SELECT category FROM agents WHERE id = $1", public.id)
    assert row["category"] == "payments", "a failed classification keeps the last category"


async def test_category_counts_match_the_filter_including_secondary(db, repo):
    def verdict(primary, secondary):
        return CardVerdict(score=0.0, signals={}, model="jev-test", category=primary, category_secondary=secondary)

    await repo.create(_agent(20), review=_review(verdict("payments", "crypto-web3"), "s20", None))
    await repo.create(_agent(21), review=_review(verdict("payments", "payments"), "s21", None))
    await repo.create(_agent(22), review=_review(verdict("crypto-web3", None), "s22", "pending"))
    deleted = await repo.create(_agent(23), review=_review(verdict("crypto-web3", None), "s23", None))
    await repo.delete(deleted.id)

    counts = await repo.count_by_category()
    assert counts == {"payments": 2, "crypto-web3": 1}  # secondary counted, same slug once, held/deleted not
    for slug, n in counts.items():
        listed, total = await repo.list_agents(category=slug, limit=50, offset=0)
        assert total == n


async def test_search_matches_card_host_and_endpoint_dedupes_on_trailing_slash(db, repo):
    created = await repo.create(_agent(30, url="https://agent30.example.com/a2a/"))

    found, _ = await repo.list_agents(search="agent30.example.com", limit=10, offset=0)
    assert [a.id for a in found] == [created.id]
    assert (await repo.get_by_endpoint_url("https://agent30.example.com/a2a")).id == created.id
    await repo.delete(created.id)
    assert await repo.get_by_endpoint_url("https://agent30.example.com/a2a") is None
