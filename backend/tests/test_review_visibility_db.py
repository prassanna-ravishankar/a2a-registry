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


@pytest.fixture
def no_rescore_cooldown():
    """For tests about snapshot pairing, not timing: the agents here were scored seconds ago."""
    from unittest.mock import patch

    with patch("worker.settings.rescore_cooldown_hours", 0):
        yield


@pytest.mark.usefixtures("no_rescore_cooldown")
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


async def test_system_note_replacement_never_clobbers_a_newer_human_note(db, repo):
    created = await repo.create(_agent(40))
    await repo.update_maintainer_notes(created.id, "system 404 note")
    await repo.update_maintainer_notes(created.id, "Human warning written mid-probe")

    assert not await repo.replace_system_note(created.id, "system 404 note", "system WORKING note")
    assert await db.fetchval("SELECT maintainer_notes FROM agents WHERE id = $1", created.id) == "Human warning written mid-probe"
    assert await repo.replace_system_note(created.id, "Human warning written mid-probe", "replaced")


async def test_snapshot_carries_the_last_score_time_for_the_rescore_cooldown(db, repo):
    from datetime import datetime, timedelta, timezone

    created = await repo.create(_agent(91), review=_review(CLEAN, "sha-cooldown", None))
    _, state = await repo.get_review_snapshot(created.id)
    checked_at = state["jev_checked_at"]
    assert checked_at.tzinfo is not None, "compared against an aware now() in assess"
    assert datetime.now(timezone.utc) - checked_at < timedelta(minutes=5)


async def _chat_failure(db, agent_id, hours_ago):
    await db.execute(
        "INSERT INTO health_checks (agent_id, status_code, response_time_ms, success, error_message, source, checked_at) "
        "VALUES ($1, 502, 10, false, 'Agent returned an unexpected error', 'chat', NOW() - make_interval(hours => $2))",
        agent_id, hours_ago,
    )


def _chat_note(agent) -> bool:
    return any(note.startswith("Returning errors when contacted by users") for note in agent.status_notes)


async def test_a_chat_failure_is_superseded_only_by_a_later_successful_chat(db, repo):
    """#226: one old chat error must not label an agent that answers users today. A passing
    task probe is not chat-path evidence, so only a successful /chat supersedes."""
    created = await repo.create(_agent(92), review=_review(CLEAN, "sha-chat", None))
    await _chat_failure(db, created.id, hours_ago=48)
    assert _chat_note(await repo.get_by_id(created.id)), "an unexplained recent failure is reported"

    await repo.update_task_conformance(created.id, "WORKING", 120)
    assert _chat_note(await repo.get_by_id(created.id)), "a passing task probe does not clear a chat failure"

    await repo.record_chat_success(created.id)
    assert not _chat_note(await repo.get_by_id(created.id))

    await _chat_failure(db, created.id, hours_ago=-0.01)
    assert _chat_note(await repo.get_by_id(created.id)), "a failure after the success is reported again"


async def test_a_chat_failure_older_than_a_week_is_not_reported(db, repo):
    created = await repo.create(_agent(93), review=_review(CLEAN, "sha-chat-old", None))
    await _chat_failure(db, created.id, hours_ago=24 * 8)
    assert not _chat_note(await repo.get_by_id(created.id))


async def _audit(db, agent_id):
    return [tuple(r) for r in await db.fetch(
        "SELECT action, previous_status, card_sha256 FROM admin_actions WHERE agent_id = $1 ORDER BY id", agent_id,
    )]


async def test_admin_can_reject_a_listing_jev_scored_clean_and_it_is_recorded(db, repo):
    """#221: a clean-scored public listing can be rejected through the API path."""
    created = await repo.create(_agent(94), review=_review(CLEAN, "sha-clean", None))
    assert await _publicly_visible(db, repo, created.id)

    assert not await repo.decide_review(created.id, approve=False, card_sha256="other-content")
    assert await repo.decide_review(created.id, approve=False, card_sha256="sha-clean")
    assert not await _publicly_visible(db, repo, created.id)
    assert await _audit(db, created.id) == [("reject", None, "sha-clean")]

    assert not await repo.decide_review(created.id, approve=False, card_sha256="sha-clean"), "already rejected"
    assert len(await _audit(db, created.id)) == 1, "a refused decision is not recorded"


async def test_approval_still_requires_a_queued_agent(db, repo):
    clean = await repo.create(_agent(95), review=_review(CLEAN, "sha-c", None))
    assert not await repo.decide_review(clean.id, approve=True, card_sha256="sha-c")
    assert await _audit(db, clean.id) == []

    queued = await repo.create(_agent(96), review=_review(FLAGGED, "sha-q", "pending"))
    assert await repo.decide_review(queued.id, approve=True, card_sha256="sha-q")
    assert await _audit(db, queued.id) == [("approve", "pending", "sha-q")]

    assert await repo.decide_review(queued.id, approve=False, card_sha256="sha-q"), "an approval can be revoked"
    assert await _audit(db, queued.id) == [("approve", "pending", "sha-q"), ("reject", "approved", "sha-q")]
    assert not await _publicly_visible(db, repo, queued.id)


async def test_admin_review_lookup_covers_held_and_clean_agents(db, repo):
    held = await repo.create(_agent(97), review=_review(FLAGGED, "sha-h", "pending"))
    state = await repo.get_admin_review(held.id)
    assert state["review_status"] == "pending" and state["jev_card_sha256"] == "sha-h"


async def test_restore_unhides_only_hidden_agents_and_keeps_moderation(db, repo):
    """#233: restore flips hidden back; a held agent still stays out of public reads."""
    clean = await repo.create(_agent(98), review=_review(CLEAN, "sha-r1", None))
    held = await repo.create(_agent(99), review=_review(FLAGGED, "sha-r2", "pending"))
    assert await repo.get_hidden_snapshot(clean.id) is None, "not hidden, nothing to restore"
    for agent in (clean, held):
        await repo.delete(agent.id)
        _, state = await repo.get_hidden_snapshot(agent.id)
        assert await repo.restore(agent.id, state["review_revision"])
        assert await repo.get_hidden_snapshot(agent.id) is None
    assert await _publicly_visible(db, repo, clean.id)
    assert not await _publicly_visible(db, repo, held.id)


async def _checks(db, agent_id, hours_ago: list[float], success=False, source="worker"):
    for h in hours_ago:
        await db.execute(
            "INSERT INTO health_checks (agent_id, status_code, response_time_ms, success, error_message, source, checked_at) "
            "VALUES ($1, $2, 10, $3, NULL, $4, NOW() - make_interval(secs => $5))",
            agent_id, 200 if success else 503, success, source, h * 3600,
        )


async def _hidden(db, agent_id) -> bool:
    return await db.fetchval("SELECT hidden FROM agents WHERE id = $1", agent_id)


async def test_restore_is_guarded_against_a_newer_retirement(db, repo):
    """#235 review P2 (ABA): hide and restore advance review_revision, so a restore based
    on an older snapshot cannot undo a later retirement."""
    agent = await repo.create(_agent(106), review=_review(CLEAN, "sha-aba", None))
    await repo.delete(agent.id)
    _, first = await repo.get_hidden_snapshot(agent.id)
    assert await repo.restore(agent.id, first["review_revision"])
    await repo.delete(agent.id)                                            # retired again
    assert not await repo.restore(agent.id, first["review_revision"]), "stale restore refused"
    assert await _hidden(db, agent.id)


async def test_changed_content_is_written_with_its_review_and_unhidden_together(db, repo):
    agent = await repo.create(_agent(107), review=_review(CLEAN, "sha-c1", None))
    await repo.delete(agent.id)
    stored, state = await repo.get_hidden_snapshot(agent.id)
    changed = _agent(107, description="changed while hidden")
    held = _review(FLAGGED, "sha-c2", "pending", expect_revision=state["review_revision"])
    assert await repo.update(agent.id, changed, review=held, unhide=True) is not None
    assert not await _hidden(db, agent.id)
    assert not await _publicly_visible(db, repo, agent.id), "flagged changed content comes back held"


async def test_dead_agent_auto_hide_works_at_the_daily_dead_check_cadence(db, repo):
    """#234: an agent already marked dead is checked once a day, so a fixed 10-failure
    threshold was never met and it stayed listed forever."""
    from worker import hide_dead_agents

    daily = await repo.create(_agent(101), review=_review(CLEAN, "sha-d1", None))
    await _checks(db, daily.id, [6.5 * 24 - 24 * d for d in range(7)])        # 7 daily failures over 6.5 days

    frequent = await repo.create(_agent(102), review=_review(CLEAN, "sha-d2", None))
    await _checks(db, frequent.id, [h / 2 for h in range(0, 2 * 24 * 7 - 4)])  # every 30 min for ~7 days

    new = await repo.create(_agent(103), review=_review(CLEAN, "sha-d3", None))
    await _checks(db, new.id, [h / 2 for h in range(0, 2 * 24 * 3)])          # failing, but only for 3 days

    recovering = await repo.create(_agent(104), review=_review(CLEAN, "sha-d4", None))
    await _checks(db, recovering.id, [6.5 * 24 - 24 * d for d in range(7)])
    await _checks(db, recovering.id, [2.0], success=True)                    # one success in the week

    restored = await repo.create(_agent(105), review=_review(CLEAN, "sha-d5", None))
    await _checks(db, restored.id, [6.5 * 24 - 24 * d for d in range(7)])
    await _checks(db, restored.id, [0.01], success=True, source="admin")     # #233 restore records a success

    await hide_dead_agents(db)
    assert await _hidden(db, daily.id) and await _hidden(db, frequent.id)
    assert not await _hidden(db, new.id), "a new agent gets the full week"
    assert not await _hidden(db, recovering.id)
    assert not await _hidden(db, restored.id), "an admin restore is not undone by the next pass"



async def test_dead_agent_auto_hide_needs_a_current_sustained_run_of_worker_failures(db, repo):
    """#236 review: sparse, stale or chat-only evidence is not a week of deadness."""
    from worker import hide_dead_agents

    stale_cluster = await repo.create(_agent(108), review=_review(CLEAN, "sha-e1", None))
    await _checks(db, stale_cluster.id, [156, 155.9, 155.8, 155.7, 155.6])   # one old burst, nothing since

    chat_mostly = await repo.create(_agent(109), review=_review(CLEAN, "sha-e2", None))
    await _checks(db, chat_mostly.id, [156])                                  # one old worker failure
    await _checks(db, chat_mostly.id, [24, 12, 6, 1], source="chat")          # chat failures are weaker evidence

    four_daily = await repo.create(_agent(110), review=_review(CLEAN, "sha-e3", None))
    await _checks(db, four_daily.id, [6.5 * 24, 4.5 * 24, 2.5 * 24, 0.5 * 24])  # only 4 worker checks

    gone_quiet = await repo.create(_agent(111), review=_review(CLEAN, "sha-e4", None))
    await _checks(db, gone_quiet.id, [6.8 * 24 - 12 * h for h in range(9)])  # failures stop 2.8 days ago

    three_days = await repo.create(_agent(113), review=_review(CLEAN, "sha-e6", None))
    # 5 checks, oldest 6.5 days and newest 1 h ago, but on only 3 UTC days.
    await _checks(db, three_days.id, [6.5 * 24, 6.5 * 24 - 0.001, 3 * 24, 3 * 24 - 0.001, 1])

    five_daily = await repo.create(_agent(112), review=_review(CLEAN, "sha-e5", None))
    await _checks(db, five_daily.id, [6.5 * 24, 5 * 24, 3.5 * 24, 2 * 24, 0.5 * 24])

    await hide_dead_agents(db)
    for kept in (stale_cluster, chat_mostly, four_daily, gone_quiet, three_days):
        assert not await _hidden(db, kept.id)
    assert await _hidden(db, five_daily.id), "5 worker failures over 4+ days, still failing"
