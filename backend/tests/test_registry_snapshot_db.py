"""GET /admin/snapshot against a real Postgres: it must say exactly what the per-resource public
endpoints say, so the static build can read one response instead of ~800.

Runs only when TEST_DATABASE_URL points at a disposable database (see tests/conftest.py).
"""

from datetime import timedelta
from unittest.mock import patch

import httpx
import pytest

from app.main import app
from app.repositories import AgentRepository

from .conftest import requires_postgres
from .test_review_visibility_db import FLAGGED, _agent, _review

pytestmark = requires_postgres


ADMIN = {"X-Admin-Key": "test-admin-key"}


@pytest.fixture
async def api(db):
    with patch("app.main.db", db), patch("app.main.settings.admin_api_key", "test-admin-key"):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test/api") as client:
            yield client


async def _check(db, agent_id, ago: timedelta, success: bool, ms: int | None = None):
    await db.execute(
        """INSERT INTO health_checks (agent_id, checked_at, status_code, response_time_ms, success, error_message)
           VALUES ($1, NOW() - $2::interval, $3, $4, $5, $6)""",
        agent_id, ago, 200 if success else 503, ms, success, None if success else "down",
    )


async def _snapshot(api):
    response = await api.get("/admin/snapshot", headers=ADMIN)
    assert response.status_code == 200
    return response.json()


async def test_snapshot_holds_exactly_the_public_agents(db, api):
    repo = AgentRepository(db)
    public = await repo.create(_agent(1))
    held = await repo.create(_agent(2), review=_review(FLAGGED, "sha-2", "pending"))
    hidden = await repo.create(_agent(3))
    await db.execute("UPDATE agents SET hidden = true WHERE id = $1", hidden.id)
    for agent in (public, held, hidden):
        await _check(db, agent.id, timedelta(hours=1), True, 40)

    snapshot = await _snapshot(api)
    listed = (await api.get("/agents", params={"limit": 100})).json()

    assert [a["id"] for a in snapshot["agents"]] == [a["id"] for a in listed["agents"]] == [str(public.id)]
    assert snapshot["agents"] == listed["agents"]
    assert snapshot["total"] == listed["total"] == 1
    assert set(snapshot["uptime"]) == {str(public.id)}


async def test_snapshot_uptime_matches_the_per_agent_endpoint(db, api):
    repo = AgentRepository(db)
    busy = await repo.create(_agent(1))      # more checks than the 100-point history
    mixed = await repo.create(_agent(2))     # failures and missing response times
    silent = await repo.create(_agent(3))    # never checked
    stale = await repo.create(_agent(4))     # only checks older than the period

    for i in range(130):
        await _check(db, busy.id, timedelta(minutes=30 * i), i % 7 != 0, 20 + i)
    for i, (ok, ms) in enumerate([(True, 100), (False, None), (True, None), (False, 900), (True, 300)]):
        await _check(db, mixed.id, timedelta(hours=i + 1), ok, ms)
    await _check(db, stale.id, timedelta(days=40), True, 10)
    await _check(db, mixed.id, timedelta(days=35), False, 5)

    snapshot = await _snapshot(api)

    for agent in (busy, mixed):
        per_agent = (await api.get(f"/agents/{agent.id}/uptime", params={"period_days": 30})).json()
        summary = snapshot["uptime"][str(agent.id)]
        for field in ("period_days", "uptime_percentage", "avg_response_time_ms", "total_checks",
                      "successful_checks", "failed_checks", "last_check"):
            assert summary[field] == per_agent[field], field
        assert summary["history"] == [
            {"checked_at": h["checked_at"], "success": h["success"]} for h in per_agent["history"]
        ]

    assert len(snapshot["uptime"][str(busy.id)]["history"]) == 100
    for agent in (silent, stale):
        assert str(agent.id) not in snapshot["uptime"]
        assert (await api.get(f"/agents/{agent.id}/uptime")).status_code == 404


async def test_snapshot_stats_and_categories_match_their_endpoints(db, api):
    repo = AgentRepository(db)
    agent = await repo.create(_agent(1))
    await _check(db, agent.id, timedelta(minutes=5), True, 50)

    snapshot = await _snapshot(api)
    stats = (await api.get("/stats")).json()

    assert {k: v for k, v in snapshot["stats"].items() if k != "generated_at"} == {
        k: v for k, v in stats.items() if k != "generated_at"
    }
    assert snapshot["categories"] == (await api.get("/categories")).json()


async def test_snapshot_is_gzipped_for_clients_that_accept_it(db, api):
    repo = AgentRepository(db)
    for n in range(5):
        await repo.create(_agent(n))

    response = await api.get("/admin/snapshot", headers={**ADMIN, "Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert len(response.json()["agents"]) == 5


async def test_snapshot_is_rendered_once_a_minute(db, api):
    repo = AgentRepository(db)
    await repo.create(_agent(1))

    first = (await _snapshot(api))["agents"]
    await repo.create(_agent(2))  # lands after the render
    assert (await _snapshot(api))["agents"] == first

    from app import main
    main.snapshot_cache._expires_at = 0  # the minute is up
    assert len((await _snapshot(api))["agents"]) == 2


async def test_snapshot_is_never_stored_by_a_shared_cache(db, api):
    response = await api.get("/admin/snapshot", headers=ADMIN)
    assert response.headers["cache-control"] == "no-store"
