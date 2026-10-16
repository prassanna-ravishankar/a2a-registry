"""Per-client limits, the service-wide Jev ceiling, and the client address they key on."""

import asyncio
import os
import time
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import rate_limits
from app.card_classifier import QUESTIONS, assess, classify_card
from app.rate_limits import (
    DAY,
    GIVE_BACK_SQL,
    SUBMIT,
    TAKE_SQL,
    USED_SQL,
    JevBudget,
    Limit,
    RateLimitError,
    client_key,
    jev_limits,
    take,
)

from .conftest import MOCK_AGENT_CARD
from .test_endpoints import _make_agent_in_db, _make_agent_public

GOOGLE_FRONTEND = "35.191.10.20"
CEILING = next(limit for limit in jev_limits(None) if limit.name == "jev")
CLOUDFLARE_EDGE = "172.70.1.2"
REGISTER = {"wellKnownURI": "https://example.com/.well-known/agent.json"}


class CounterDb:
    """The suite's mock db plus an in-memory rate_limit_counters table with the SQL's semantics."""

    def __init__(self, base):
        self.base = base
        self.rows: dict[tuple[str, int], int] = {}

    async def fetchval(self, query, *args):
        if query == TAKE_SQL:
            scope, window_end, cost, limit = args
            used = self.rows.get((scope, window_end))
            if used is not None and used + cost > limit:
                return None
            self.rows[(scope, window_end)] = (used or 0) + cost
            return self.rows[(scope, window_end)]
        if query == USED_SQL:
            return self.rows.get(args)
        return await self.base.fetchval(query, *args)

    async def execute(self, query, *args):
        if query == GIVE_BACK_SQL:
            self.rows[(args[0], args[1])] -= args[2]
            return "UPDATE 1"
        return await self.base.execute(query, *args)

    def __getattr__(self, name):
        return getattr(self.base, name)

    def used(self, scope: str) -> int:
        return sum(used for (name, _), used in self.rows.items() if name == scope)

    def exhaust(self, limit: Limit) -> None:
        end = (int(time.time()) // limit.seconds + 1) * limit.seconds
        self.rows[(limit.name, end)] = limit.count


def _request(peer: str, headers: dict[str, str] | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "client": (peer, 1234), "headers": raw})


def _via_cloudflare(ip: str) -> dict[str, str]:
    return {"x-forwarded-for": f"6.6.6.6, {ip}, {CLOUDFLARE_EDGE}, 34.1.1.1", "cf-connecting-ip": ip}


# --- client address -------------------------------------------------------


@pytest.mark.parametrize(
    ("peer", "headers", "expected"),
    [
        ("203.0.113.9", {}, "203.0.113.9"),
        ("203.0.113.9", {"x-forwarded-for": "1.2.3.4", "cf-connecting-ip": "1.2.3.4"}, "203.0.113.9"),
        (GOOGLE_FRONTEND, _via_cloudflare("198.51.100.7"), "198.51.100.7"),
        (GOOGLE_FRONTEND, {"x-forwarded-for": "1.2.3.4, 198.51.100.7, 34.1.1.1", "cf-connecting-ip": "1.2.3.4"},
         "198.51.100.7"),
        (GOOGLE_FRONTEND, _via_cloudflare("2001:db8:1:2:aaaa::1"), "2001:db8:1:2::/64"),
        ("testclient", {}, "testclient"),
    ],
    ids=["direct-peer", "forged-headers-not-from-gateway", "cloudflare", "gateway-bypassing-cloudflare",
         "ipv6-by-64", "non-ip-peer"],
)
def test_client_key_trusts_only_hops_the_infrastructure_appended(peer, headers, expected):
    assert client_key(_request(peer, headers)) == expected


# --- counting -------------------------------------------------------------


async def test_take_is_all_or_nothing():
    db = CounterDb(MagicMock())
    wide, narrow = Limit("wide", 10, DAY, "m"), Limit("narrow", 2, DAY, "m")
    await take(db, [wide, narrow], 2)
    with pytest.raises(RateLimitError) as refused:
        await take(db, [wide, narrow], 1)
    assert refused.value.limit is narrow
    assert 1 <= refused.value.retry_after <= DAY
    assert db.used("wide") == 2, "the wider counter is given back when a later one refuses"


async def test_a_cost_larger_than_the_limit_is_refused_without_counting():
    db = CounterDb(MagicMock())
    with pytest.raises(RateLimitError):
        await take(db, [Limit("small", 5, DAY, "m")], 6)
    assert db.rows == {}


# --- per-client limits on endpoints ---------------------------------------


@pytest.fixture
def counters(mock_db):
    db = CounterDb(mock_db)
    with patch("app.main.db", db):
        yield db


@pytest.fixture
def api(counters):
    from app.main import app

    with TestClient(app, raise_server_exceptions=False, client=(GOOGLE_FRONTEND, 1234)) as c:
        yield c


def _registration_mocks(stack):
    repo = stack.enter_context(patch("app.main.AgentRepository")).return_value
    stack.enter_context(patch("app.main.validate_well_known_uri", return_value=[]))
    fetch = stack.enter_context(patch("app.main.fetch_agent_card", return_value=(MOCK_AGENT_CARD, None)))
    stack.enter_context(patch("app.main.smoke_test", new=AsyncMock(return_value=("WORKING", "ok", 10))))
    for name in ("get_by_well_known_uri", "get_by_host", "get_by_name_and_author", "get_by_endpoint_url"):
        setattr(repo, name, AsyncMock(return_value=None))
    repo.create = AsyncMock(return_value=_make_agent_in_db())
    repo.update_maintainer_notes = AsyncMock(return_value=True)
    repo.update_task_conformance = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=_make_agent_public())
    return repo, fetch


def _post_register(api, ip, path="/agents/register"):
    full = {
        "protocolVersion": "0.3.0", "name": "Test Agent", "description": "d", "author": "Test Author",
        "url": "https://example.com/a2a", "version": "1.0.0", "capabilities": {}, "skills": [],
        "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"], **REGISTER,
    }
    body = REGISTER if path == "/agents/register" else full
    return api.post(path, json=body, headers=_via_cloudflare(ip))


def test_submissions_are_limited_per_client_across_both_endpoints(api):
    hourly = SUBMIT[0].count
    with ExitStack() as stack:
        repo, fetch = _registration_mocks(stack)
        codes = [_post_register(api, "198.51.100.7").status_code for _ in range(hourly)]
        fetches = fetch.call_count
        refused = _post_register(api, "198.51.100.7", path="/agents")
        other_client = _post_register(api, "198.51.100.8")

    assert codes == [201] * hourly
    assert refused.status_code == 429
    assert 1 <= int(refused.headers["Retry-After"]) <= 3600
    assert "Retry-After" in refused.json()["detail"]
    assert fetch.call_count == fetches + 1, "a refused submission fetches nothing; the other client's does"
    assert other_client.status_code == 201


def test_spoofed_forwarded_for_does_not_reset_the_limit(api):
    with ExitStack() as stack:
        _registration_mocks(stack)
        codes = []
        for n in range(SUBMIT[0].count + 1):
            # The client controls everything before the hops Cloudflare and Google append.
            headers = {"x-forwarded-for": f"10.0.0.{n}, 198.51.100.7, {CLOUDFLARE_EDGE}, 34.1.1.1",
                       "cf-connecting-ip": "198.51.100.7"}
            codes.append(api.post("/agents/register", json=REGISTER, headers=headers).status_code)
    assert codes[-1] == 429


def test_recheck_is_limited_per_agent_across_clients(api, counters):
    agent = _make_agent_public()
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.smoke_test", new=AsyncMock(return_value=("WORKING", "ok", 10))) as probe, \
         patch("app.main.refresh_recovery_notes", new=AsyncMock()):
        mock_repo.return_value.get_by_id = AsyncMock(return_value=agent)
        mock_repo.return_value.update_task_conformance = AsyncMock()
        codes = [
            api.post(f"/agents/{agent.id}/recheck", headers=_via_cloudflare(f"198.51.100.{n}")).status_code
            for n in range(rate_limits.RECHECK_AGENT.count + 1)
        ]
    assert codes[:-1] == [200] * rate_limits.RECHECK_AGENT.count
    assert codes[-1] == 429
    assert probe.await_count == rate_limits.RECHECK_AGENT.count


# --- the service-wide Jev ceiling -----------------------------------------


@pytest.mark.parametrize("scope", ["jev", "jev-submissions", "jev-submissions-hour"])
def test_exhausted_global_budget_refuses_every_client_before_any_work(api, counters, clean_jev_verdict, scope):
    counters.exhaust(next(limit for limit in jev_limits("x") if limit.name == scope))
    with ExitStack() as stack:
        repo, fetch = _registration_mocks(stack)
        responses = [_post_register(api, f"198.51.100.{n}") for n in range(3)]

    assert {r.status_code for r in responses} == {429}
    assert all(int(r.headers["Retry-After"]) >= 1 for r in responses)
    assert "review capacity" in responses[0].json()["detail"]
    fetch.assert_not_called()
    repo.create.assert_not_awaited()
    clean_jev_verdict.assert_not_awaited()


def test_budget_exhausted_mid_flight_never_calls_jev_and_stores_nothing(api, counters):
    """The pre-check passed, then other submissions took the last of the budget."""
    jev = SimpleNamespace(system_one=AsyncMock())
    ceiling = CEILING
    with ExitStack() as stack:
        repo, _ = _registration_mocks(stack)
        stack.enter_context(patch("app.card_classifier.classify_card", new=classify_card))
        stack.enter_context(patch("app.card_classifier._get_client", return_value=jev))
        stack.enter_context(patch("app.main.smoke_test", new=AsyncMock(
            side_effect=lambda *a, **k: counters.exhaust(ceiling) or ("WORKING", "ok", 10),
        )))
        response = _post_register(api, "198.51.100.7")

    assert response.status_code == 429
    jev.system_one.assert_not_awaited()
    repo.create.assert_not_awaited()


def test_registration_reserves_one_request_per_card_window(api, counters):
    reply = SimpleNamespace(
        model="jev-test",
        answers={name: SimpleNamespace(noul=0.0) for name in QUESTIONS},
    )
    jev = SimpleNamespace(system_one=AsyncMock(return_value=reply))
    with ExitStack() as stack:
        _registration_mocks(stack)
        stack.enter_context(patch("app.card_classifier.classify_card", new=classify_card))
        stack.enter_context(patch("app.card_classifier._get_client", return_value=jev))
        response = _post_register(api, "198.51.100.7")

    sent = jev.system_one.await_count
    assert response.status_code == 201 and sent >= 1
    for scope in ("jev", "jev-submissions", "jev-submissions-hour", "jev-client:198.51.100.7"):
        assert counters.used(scope) == sent


def test_a_busy_worker_day_never_refuses_submitters(api, counters):
    background = next(limit for limit in jev_limits(None) if limit.name == "jev-background")
    counters.exhaust(background)
    with ExitStack() as stack:
        _registration_mocks(stack)
        response = _post_register(api, "198.51.100.7")
    assert response.status_code == 201


async def test_a_submission_flood_never_starves_the_worker():
    db = CounterDb(MagicMock())
    db.exhaust(next(limit for limit in jev_limits("x") if limit.name == "jev-submissions"))
    await JevBudget(db).reserve(5)
    with pytest.raises(RateLimitError):
        await JevBudget(db, "198.51.100.7").reserve(1)
    assert db.used("jev-background") == 5 and db.used("jev") == 5


def test_the_shares_partition_the_ceiling():
    background = next(limit for limit in jev_limits(None) if limit.name == "jev-background")
    submissions = next(limit for limit in jev_limits("x") if limit.name == "jev-submissions")
    assert background.count + submissions.count == CEILING.count
    assert CEILING in jev_limits(None) and CEILING in jev_limits("x")


def test_admin_update_stops_at_the_ceiling(api, counters, clean_jev_verdict):
    counters.exhaust(CEILING)
    with patch("app.main.settings") as settings, patch("app.main.fetch_agent_card") as fetch:
        settings.admin_api_key = "k"
        response = api.put(f"/agents/{_make_agent_public().id}", headers={"X-Admin-Key": "k"})
    assert response.status_code == 429 and "Retry-After" in response.headers
    fetch.assert_not_called()
    clean_jev_verdict.assert_not_awaited()


async def test_worker_defers_a_changed_card_when_the_ceiling_is_reached():
    jev = SimpleNamespace(system_one=AsyncMock())
    budget = SimpleNamespace(reserve=AsyncMock(side_effect=RateLimitError(CEILING, 60)))
    with patch("app.card_classifier.classify_card", new=classify_card), \
         patch("app.card_classifier._get_client", return_value=jev), \
         pytest.raises(RateLimitError):
        await assess({"jev_card_sha256": "old"}, {"record": {"name": "x"}}, budget=budget, may_grandfather=True)
    jev.system_one.assert_not_awaited()


async def test_worker_refresh_writes_nothing_when_the_budget_refuses():
    import worker

    stored = _make_agent_public()
    repo = SimpleNamespace(
        get_review_snapshot=AsyncMock(return_value=(stored, {"jev_card_sha256": "old", "review_revision": 1})),
        update_card_metadata=AsyncMock(),
    )
    with patch("worker.assess", new=AsyncMock(side_effect=RateLimitError(CEILING, 60))), \
         patch.object(worker, "_material_changes", return_value=({}, {})), \
         pytest.raises(RateLimitError):
        await worker.refresh_agent_metadata(stored, dict(MOCK_AGENT_CARD), repo, conformance_errors=[], classify=True)
    repo.update_card_metadata.assert_not_awaited()


def _validation_error():
    from typesafe_sdk import TypeSafeAPIResponseValidationError

    return TypeSafeAPIResponseValidationError.__new__(TypeSafeAPIResponseValidationError)


@pytest.mark.parametrize("failure", ["exhausted", "limiter_down"])
def test_budget_failure_during_the_fallback_writes_nothing(api, counters, failure):
    """The first reservation succeeds; the moderation-only retry's reservation does not."""
    ceiling = CEILING
    original = counters.fetchval

    def break_budget():
        if failure == "exhausted":
            counters.exhaust(ceiling)
        else:
            async def down(query, *args):
                if query == TAKE_SQL:
                    raise TimeoutError
                return await original(query, *args)
            counters.fetchval = down
        raise _validation_error()

    jev = SimpleNamespace(system_one=AsyncMock(side_effect=lambda *a, **k: break_budget()))
    with ExitStack() as stack:
        repo, _ = _registration_mocks(stack)
        stack.enter_context(patch("app.card_classifier.classify_card", new=classify_card))
        stack.enter_context(patch("app.card_classifier._get_client", return_value=jev))
        response = _post_register(api, "198.51.100.7")

    assert response.status_code == (429 if failure == "exhausted" else 503)
    assert "Retry-After" in response.headers
    assert jev.system_one.await_count == 1, "the refused fallback is never sent"
    repo.create.assert_not_awaited()
    repo.update_maintainer_notes.assert_not_awaited()


@pytest.mark.parametrize(
    "refusal",
    [RateLimitError(Limit("jev", 1, DAY, "m"), 60), TimeoutError()],
    ids=["exhausted", "limiter_down"],
)
async def test_worker_writes_nothing_when_the_fallback_reservation_fails(refusal):
    import worker

    stored = _make_agent_public()
    repo = SimpleNamespace(
        get_review_snapshot=AsyncMock(return_value=(stored, {"jev_card_sha256": "old", "review_revision": 1})),
        update_card_metadata=AsyncMock(),
    )
    # The first reservation takes both worker counters; the fallback's first take fails.
    budget_db = SimpleNamespace(fetchval=AsyncMock(side_effect=[1, 1, refusal]), execute=AsyncMock())
    if isinstance(refusal, RateLimitError):
        budget = SimpleNamespace(reserve=AsyncMock(side_effect=[None, refusal]))
    else:
        budget = JevBudget(budget_db)
    jev = SimpleNamespace(system_one=AsyncMock(side_effect=_validation_error()))
    with patch("app.card_classifier.classify_card", new=classify_card), \
         patch("app.card_classifier._get_client", return_value=jev), \
         patch("worker.JevBudget", return_value=budget), \
         patch.object(worker, "_material_changes", return_value=({}, {"name": "x"})), \
         pytest.raises(rate_limits.NOT_SENT):
        await worker.refresh_agent_metadata(stored, dict(MOCK_AGENT_CARD), repo, conformance_errors=[], classify=True)
    assert jev.system_one.await_count == 1
    repo.update_card_metadata.assert_not_awaited()


async def test_sdk_retries_are_off_so_each_reserved_request_is_one_http_attempt():
    import httpx2

    from app import card_classifier

    attempts = []

    def unavailable(request):
        attempts.append(request)
        return httpx2.Response(503, json={"error": "unavailable"})

    real = card_classifier.AsyncTypeSafeClient
    budget = SimpleNamespace(reserve=AsyncMock())
    with patch("app.card_classifier.classify_card", new=classify_card), \
         patch("app.card_classifier._client", None), \
         patch("app.card_classifier.settings.jev_api_key", "k"), \
         patch("app.card_classifier.AsyncTypeSafeClient",
               side_effect=lambda **kw: real(**kw, transport=httpx2.MockTransport(unavailable))):
        review = await assess({}, {"record": {"name": "x"}}, budget=budget, may_grandfather=False)
    assert review.verdict is None
    assert len(attempts) == sum(call.args[0] for call in budget.reserve.await_args_list) == 1


# --- the SQL against a real Postgres ---------------------------------------

DB_URL = os.environ.get("TEST_DATABASE_URL")
MIGRATIONS = sorted((Path(__file__).parent.parent / "migrations" / "versions").glob("*.sql"))


@pytest.fixture
async def pg():
    if not DB_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=8)
    await pool.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    for migration in MIGRATIONS:
        await pool.execute(migration.read_text())
    yield pool
    await pool.close()


async def test_counters_against_postgres(pg):
    limit = Limit("pg", 5, DAY, "m")
    results = await asyncio.gather(*(take(pg, [limit]) for _ in range(8)), return_exceptions=True)
    assert sum(r is None for r in results) == 5
    assert sum(isinstance(r, RateLimitError) for r in results) == 3
    assert await pg.fetchval("SELECT used FROM rate_limit_counters WHERE scope = 'pg'") == 5

    await pg.execute("UPDATE rate_limit_counters SET window_end = 1")
    await rate_limits.prune(pg)
    assert await pg.fetchval("SELECT count(*) FROM rate_limit_counters") == 0


async def test_jev_budget_against_postgres(pg):
    budget = JevBudget(pg, "198.51.100.7")
    await budget.reserve(3)
    rows = dict(await pg.fetch("SELECT scope, used FROM rate_limit_counters"))
    assert rows == {limit.name: 3 for limit in jev_limits("198.51.100.7")}
    await budget.ensure_available()
