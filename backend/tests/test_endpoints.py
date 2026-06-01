"""Tests for registration, update, delete, flagging, health, notes, and SSRF protection."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

from app.main import _is_private_url
from app.models import AgentInDB, AgentPublic, Capabilities

from .conftest import MOCK_AGENT_CARD, MOCK_AGENT_ROW

MOCK_UUID = "550e8400-e29b-41d4-a716-446655440000"
OTHER_UUID = "660e8400-e29b-41d4-a716-446655440001"


def _make_agent_in_db(**overrides):
    caps = json.loads(MOCK_AGENT_ROW["capabilities"])
    defaults = dict(
        id=UUID(MOCK_AGENT_ROW["id"]),
        created_at=datetime.fromisoformat(MOCK_AGENT_ROW["created_at"]),
        updated_at=datetime.fromisoformat(MOCK_AGENT_ROW["updated_at"]),
        hidden=MOCK_AGENT_ROW["hidden"],
        flag_count=MOCK_AGENT_ROW["flag_count"],
        protocolVersion=MOCK_AGENT_ROW["protocol_version"],
        name=MOCK_AGENT_ROW["name"],
        description=MOCK_AGENT_ROW["description"],
        author=MOCK_AGENT_ROW["author"],
        wellKnownURI=MOCK_AGENT_ROW["well_known_uri"],
        url=MOCK_AGENT_ROW["url"],
        version=MOCK_AGENT_ROW["version"],
        provider=None,
        documentationUrl=None,
        capabilities=Capabilities(**caps),
        defaultInputModes=json.loads(MOCK_AGENT_ROW["default_input_modes"]),
        defaultOutputModes=json.loads(MOCK_AGENT_ROW["default_output_modes"]),
        skills=[],
        conformance=None,
    )
    defaults.update(overrides)
    return AgentInDB(**defaults)


def _make_agent_public(**overrides):
    agent = _make_agent_in_db()
    defaults = dict(
        **agent.model_dump(),
        uptime_percentage=100.0,
        avg_response_time_ms=50,
        last_health_check=datetime.fromisoformat("2024-01-01T00:00:00"),
        is_healthy=True,
    )
    defaults.update(overrides)
    return AgentPublic(**defaults)


# ============================================================================
# Registration (POST /agents/register)
# ============================================================================


def test_register_agent_success(client):
    """Successful registration fetches card and creates agent."""
    mock_public = _make_agent_public()

    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.validate_well_known_uri", return_value=[]), \
         patch("app.main.fetch_agent_card", return_value=(MOCK_AGENT_CARD, None)), \
         patch("app.main.smoke_test", new=AsyncMock(return_value=("WORKING", "Verified working at registration.", 123))):
        instance = mock_repo.return_value
        instance.get_by_well_known_uri = AsyncMock(return_value=None)
        instance.get_by_host = AsyncMock(return_value=None)
        instance.get_by_name_and_author = AsyncMock(return_value=None)
        instance.create = AsyncMock(return_value=_make_agent_in_db())
        instance.update_maintainer_notes = AsyncMock(return_value=True)
        instance.update_task_conformance = AsyncMock(return_value=None)
        instance.get_by_id = AsyncMock(return_value=mock_public)

        response = client.post(
            "/agents/register",
            json={"wellKnownURI": "https://example.com/.well-known/agent.json"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Test Agent"


def test_register_agent_smoke_test_rejects_no_transports(client):
    """Hard-reject when smoke test reports NO_TRANSPORTS."""
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.validate_well_known_uri", return_value=[]), \
         patch("app.main.fetch_agent_card", return_value=(MOCK_AGENT_CARD, None)), \
         patch("app.main.smoke_test", new=AsyncMock(return_value=("NO_TRANSPORTS", "Agent card does not declare any transports compatible with the A2A SDK", None))):
        instance = mock_repo.return_value
        instance.get_by_well_known_uri = AsyncMock(return_value=None)
        instance.get_by_host = AsyncMock(return_value=None)
        instance.get_by_name_and_author = AsyncMock(return_value=None)

        response = client.post(
            "/agents/register",
            json={"wellKnownURI": "https://example.com/.well-known/agent.json"},
        )

    assert response.status_code == 400
    assert "transports" in response.json()["detail"].lower()


def test_register_agent_smoke_test_failure_attaches_note(client):
    """Soft failures (e.g. 404) still register but get the note attached."""
    mock_public = _make_agent_public()
    note = "Agent card is valid but the A2A endpoint returns **404 Not Found** when sending messages."

    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.validate_well_known_uri", return_value=[]), \
         patch("app.main.fetch_agent_card", return_value=(MOCK_AGENT_CARD, None)), \
         patch("app.main.smoke_test", new=AsyncMock(return_value=("404", note, 87))):
        instance = mock_repo.return_value
        instance.get_by_well_known_uri = AsyncMock(return_value=None)
        instance.get_by_host = AsyncMock(return_value=None)
        instance.get_by_name_and_author = AsyncMock(return_value=None)
        instance.create = AsyncMock(return_value=_make_agent_in_db())
        instance.update_maintainer_notes = AsyncMock(return_value=True)
        instance.update_task_conformance = AsyncMock(return_value=None)
        instance.get_by_id = AsyncMock(return_value=mock_public)

        response = client.post(
            "/agents/register",
            json={"wellKnownURI": "https://example.com/.well-known/agent.json"},
        )

    assert response.status_code == 201
    instance.update_maintainer_notes.assert_awaited_once()
    args = instance.update_maintainer_notes.await_args
    assert args.args[1] == note


def test_register_agent_invalid_uri(client):
    """Reject registration with invalid wellKnownURI path."""
    response = client.post(
        "/agents/register",
        json={"wellKnownURI": "https://example.com/not-valid-path.json"},
    )
    assert response.status_code == 400


def test_register_agent_fetch_fails(client):
    """Return 400 when agent card fetch fails."""
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.validate_well_known_uri", return_value=[]), \
         patch("app.main.fetch_agent_card", return_value=(None, "Connection refused")):
        instance = mock_repo.return_value
        instance.get_by_well_known_uri = AsyncMock(return_value=None)
        instance.get_by_host = AsyncMock(return_value=None)

        response = client.post(
            "/agents/register",
            json={"wellKnownURI": "https://example.com/.well-known/agent.json"},
        )

    assert response.status_code == 400
    assert "Connection refused" in response.json()["detail"]


def test_register_agent_host_duplicate(client):
    """Reject registration when another agent from the same host exists."""
    existing = _make_agent_in_db()

    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.validate_well_known_uri", return_value=[]):
        instance = mock_repo.return_value
        instance.get_by_well_known_uri = AsyncMock(return_value=None)
        instance.get_by_host = AsyncMock(return_value=existing)

        response = client.post(
            "/agents/register",
            json={"wellKnownURI": "https://example.com/.well-known/agent-card.json"},
        )

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


def test_register_agent_card_content_duplicate(client):
    """Reject registration when the same (name, author) is already registered from a different host."""
    existing = _make_agent_in_db()

    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.validate_well_known_uri", return_value=[]), \
         patch("app.main.fetch_agent_card", return_value=(MOCK_AGENT_CARD, None)):
        instance = mock_repo.return_value
        instance.get_by_well_known_uri = AsyncMock(return_value=None)
        instance.get_by_host = AsyncMock(return_value=None)
        instance.get_by_name_and_author = AsyncMock(return_value=existing)

        response = client.post(
            "/agents/register",
            json={"wellKnownURI": "https://other-host.example.com/.well-known/agent.json"},
        )

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


# ============================================================================
# Get Agent (GET /agents/{id})
# ============================================================================


def test_get_agent_success(client):
    """Get an agent by ID returns full public model."""
    mock_public = _make_agent_public()

    with patch("app.main.AgentRepository") as mock_repo:
        instance = mock_repo.return_value
        instance.get_by_id = AsyncMock(return_value=mock_public)

        response = client.get(f"/agents/{MOCK_UUID}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Test Agent"
    assert body["is_healthy"] is True


# ============================================================================
# Update Agent (PUT /agents/{id})
# ============================================================================


def test_update_agent_success(client):
    """PUT re-fetches agent card and updates."""
    existing = _make_agent_public()
    updated_card = {**MOCK_AGENT_CARD, "name": "Updated Agent"}

    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.fetch_agent_card", return_value=(updated_card, None)):
        instance = mock_repo.return_value
        instance.get_by_id = AsyncMock(return_value=existing)
        instance.update = AsyncMock(return_value=_make_agent_in_db())

        response = client.put(f"/agents/{MOCK_UUID}")

    assert response.status_code == 200


def test_update_agent_not_found(client):
    """PUT on nonexistent agent returns 404."""
    with patch("app.main.AgentRepository") as mock_repo:
        instance = mock_repo.return_value
        instance.get_by_id = AsyncMock(return_value=None)

        response = client.put(f"/agents/{MOCK_UUID}")

    assert response.status_code == 404


def test_update_agent_fetch_fails(client):
    """PUT returns 400 when re-fetch of agent card fails."""
    existing = _make_agent_public()

    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.fetch_agent_card", return_value=(None, "Timeout")):
        instance = mock_repo.return_value
        instance.get_by_id = AsyncMock(return_value=existing)

        response = client.put(f"/agents/{MOCK_UUID}")

    assert response.status_code == 400
    assert "Timeout" in response.json()["detail"]


# --- #133: PUT must honor a wellKnownURI in the request body ----------------
#
# update_agent used to read wellKnownURI only from the existing DB row and
# ignore the request body, so an agent stuck on a dead URL could never be
# pointed at a live one — every PUT re-fetched the dead URL and 404'd. These
# tests pin that a body wellKnownURI is fetched/validated/persisted, while a
# no-body PUT still re-fetches the existing URI (backward compatible).

NEW_URI = "https://new-live-host.example/.well-known/agent-card.json"


def test_update_agent_uses_body_well_known_uri(client):
    """PUT with a new wellKnownURI fetches and persists the NEW url, not the old one."""
    existing = _make_agent_public()  # wellKnownURI = https://example.com/.well-known/agent.json
    updated_card = {**MOCK_AGENT_CARD, "name": "Moved Agent"}

    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.validate_well_known_uri", return_value=[]), \
         patch("app.main.fetch_agent_card", return_value=(updated_card, None)) as mock_fetch, \
         patch("app.main._agent_create_from_card") as mock_build:
        instance = mock_repo.return_value
        instance.get_by_id = AsyncMock(return_value=existing)
        instance.get_by_well_known_uri = AsyncMock(return_value=None)
        instance.get_by_host = AsyncMock(return_value=None)
        instance.update = AsyncMock(return_value=_make_agent_in_db())
        mock_build.return_value = _make_agent_in_db()

        response = client.put(f"/agents/{MOCK_UUID}", json={"wellKnownURI": NEW_URI})

    assert response.status_code == 200
    # The NEW url was fetched — not the stale existing one.
    mock_fetch.assert_called_once_with(NEW_URI)
    # And the new url is what gets persisted (passed to the card->row builder).
    assert mock_build.call_args[0][1] == NEW_URI


def test_update_agent_no_body_refetches_existing(client):
    """PUT with no body re-fetches the existing wellKnownURI (backward compatible)."""
    existing = _make_agent_public()

    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.fetch_agent_card", return_value=(MOCK_AGENT_CARD, None)) as mock_fetch:
        instance = mock_repo.return_value
        instance.get_by_id = AsyncMock(return_value=existing)
        instance.update = AsyncMock(return_value=_make_agent_in_db())

        response = client.put(f"/agents/{MOCK_UUID}")

    assert response.status_code == 200
    mock_fetch.assert_called_once_with(str(existing.wellKnownURI))


def test_update_agent_body_uri_conflict(client):
    """PUT to a wellKnownURI owned by a different agent returns 409."""
    existing = _make_agent_public()
    other = _make_agent_in_db(id=UUID(OTHER_UUID), name="Other Agent")

    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.validate_well_known_uri", return_value=[]):
        instance = mock_repo.return_value
        instance.get_by_id = AsyncMock(return_value=existing)
        instance.get_by_well_known_uri = AsyncMock(return_value=other)

        response = client.put(f"/agents/{MOCK_UUID}", json={"wellKnownURI": NEW_URI})

    assert response.status_code == 409
    assert OTHER_UUID in response.json()["detail"]


async def test_repo_update_persists_well_known_uri():
    """Repo-level regression for #133: AgentRepository.update() must write the
    well_known_uri column, else a body-supplied URI is fetched but never
    persisted and the worker keeps health-checking the dead URL.

    Endpoint mock tests can't catch this (they stop at _agent_create_from_card),
    so this drives the real UPDATE through a fake db and asserts the SQL sets
    well_known_uri and binds the new URI.
    """
    from app.repositories import AgentRepository

    captured = {}

    async def fake_fetchrow(query, *params):
        captured["query"] = query
        captured["params"] = params
        return MOCK_AGENT_ROW

    db = AsyncMock()
    db.fetchrow = fake_fetchrow

    agent = _make_agent_in_db(wellKnownURI=NEW_URI)
    await AgentRepository(db).update(UUID(MOCK_UUID), agent)

    sql = " ".join(captured["query"].split()).lower()
    assert "well_known_uri = $1" in sql
    # well_known_uri is $1, so the new URI must be the first bound param.
    # (HttpUrl may normalize, so compare on prefix.)
    assert str(captured["params"][0]).startswith(NEW_URI), (
        f"new wellKnownURI not bound to well_known_uri = $1; params={captured['params']}"
    )


# ============================================================================
# Delete Agent (DELETE /agents/{id})
# ============================================================================


def test_delete_agent_requires_admin(client):
    """DELETE without admin key returns 403."""
    response = client.delete(f"/agents/{MOCK_UUID}")
    assert response.status_code == 403


def test_delete_agent_wrong_admin_key(client):
    """DELETE with wrong admin key returns 403."""
    response = client.delete(
        f"/agents/{MOCK_UUID}",
        headers={"X-Admin-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_delete_agent_success(client):
    """DELETE with correct admin key soft-deletes agent."""
    existing = _make_agent_public()

    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.settings") as mock_settings:
        mock_settings.admin_api_key = "test-admin-key"
        mock_settings.rate_limit_enabled = True
        mock_settings.cors_origins = ["*"]
        instance = mock_repo.return_value
        instance.get_by_id = AsyncMock(return_value=existing)
        instance.delete = AsyncMock(return_value=True)

        response = client.delete(
            f"/agents/{MOCK_UUID}",
            headers={"X-Admin-Key": "test-admin-key"},
        )

    assert response.status_code == 204


def test_delete_agent_not_found(client):
    """DELETE on nonexistent agent returns 404."""
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.settings") as mock_settings:
        mock_settings.admin_api_key = "test-admin-key"
        mock_settings.rate_limit_enabled = True
        mock_settings.cors_origins = ["*"]
        instance = mock_repo.return_value
        instance.get_by_id = AsyncMock(return_value=None)

        response = client.delete(
            f"/agents/{MOCK_UUID}",
            headers={"X-Admin-Key": "test-admin-key"},
        )

    assert response.status_code == 404


# ============================================================================
# Maintainer Notes (PATCH /agents/{id}/notes)
# ============================================================================


def test_update_notes_requires_admin(client):
    """PATCH notes without admin key returns 403."""
    response = client.patch(
        f"/agents/{MOCK_UUID}/notes",
        json={"notes": "test note"},
    )
    assert response.status_code == 403


def test_update_notes_success(client):
    """PATCH notes with admin key updates notes."""
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.settings") as mock_settings:
        mock_settings.admin_api_key = "test-admin-key"
        mock_settings.rate_limit_enabled = True
        mock_settings.cors_origins = ["*"]
        instance = mock_repo.return_value
        instance.update_maintainer_notes = AsyncMock(return_value=True)

        response = client.patch(
            f"/agents/{MOCK_UUID}/notes",
            json={"notes": "Verified working."},
            headers={"X-Admin-Key": "test-admin-key"},
        )

    assert response.status_code == 200
    assert response.json()["maintainer_notes"] == "Verified working."


def test_clear_notes_success(client):
    """PATCH notes with null clears notes."""
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.settings") as mock_settings:
        mock_settings.admin_api_key = "test-admin-key"
        mock_settings.rate_limit_enabled = True
        mock_settings.cors_origins = ["*"]
        instance = mock_repo.return_value
        instance.update_maintainer_notes = AsyncMock(return_value=True)

        response = client.patch(
            f"/agents/{MOCK_UUID}/notes",
            json={"notes": None},
            headers={"X-Admin-Key": "test-admin-key"},
        )

    assert response.status_code == 200
    assert response.json()["maintainer_notes"] is None


def test_update_notes_agent_not_found(client):
    """PATCH notes on nonexistent agent returns 404."""
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.settings") as mock_settings:
        mock_settings.admin_api_key = "test-admin-key"
        mock_settings.rate_limit_enabled = True
        mock_settings.cors_origins = ["*"]
        instance = mock_repo.return_value
        instance.update_maintainer_notes = AsyncMock(return_value=False)

        response = client.patch(
            f"/agents/{MOCK_UUID}/notes",
            json={"notes": "test"},
            headers={"X-Admin-Key": "test-admin-key"},
        )

    assert response.status_code == 404


# ============================================================================
# Flagging (POST /agents/{id}/flag)
# ============================================================================


def test_flag_agent_success(client):
    """Flag an agent with valid reason."""
    with patch("app.main.FlagRepository") as mock_flag_repo, \
         patch("app.main.AgentRepository") as mock_agent_repo:
        mock_flag_repo.return_value.create_flag = AsyncMock(return_value=None)
        mock_agent_repo.return_value.increment_flag_count = AsyncMock(return_value=None)

        response = client.post(
            f"/agents/{MOCK_UUID}/flag",
            json={"agent_id": MOCK_UUID, "reason": "spam", "details": "This is spam"},
        )

    assert response.status_code == 201
    assert response.json()["message"] == "Flag recorded"


def test_flag_agent_invalid_reason(client):
    """Flag with invalid reason returns 422."""
    response = client.post(
        f"/agents/{MOCK_UUID}/flag",
        json={"agent_id": MOCK_UUID, "reason": "not_a_valid_reason"},
    )
    assert response.status_code == 422


# ============================================================================
# List Agents Filtering (GET /agents)
# ============================================================================


def test_list_agents_with_search(client):
    """Search param is passed to repository."""
    mock_public = _make_agent_public()

    with patch("app.main.AgentRepository") as mock_repo:
        instance = mock_repo.return_value
        instance.list_agents = AsyncMock(return_value=([mock_public], 1))

        response = client.get("/agents?search=test")

    assert response.status_code == 200
    instance.list_agents.assert_called_once()
    call_kwargs = instance.list_agents.call_args[1]
    assert call_kwargs["search"] == "test"


def test_list_agents_limit_capped(client):
    """Limit > 100 is capped to 100."""
    mock_public = _make_agent_public()

    with patch("app.main.AgentRepository") as mock_repo:
        instance = mock_repo.return_value
        instance.list_agents = AsyncMock(return_value=([mock_public], 1))

        response = client.get("/agents?limit=500")

    assert response.status_code == 200
    call_kwargs = instance.list_agents.call_args[1]
    assert call_kwargs["limit"] == 100


def test_list_agents_conformance_filter(client):
    """Conformance filter values are validated."""
    mock_public = _make_agent_public()

    with patch("app.main.AgentRepository") as mock_repo:
        instance = mock_repo.return_value
        instance.list_agents = AsyncMock(return_value=([mock_public], 1))

        # Valid value
        client.get("/agents?conformance=standard")
        assert instance.list_agents.call_args[1]["conformance"] == "standard"

        # Invalid value gets set to None
        client.get("/agents?conformance=invalid")
        assert instance.list_agents.call_args[1]["conformance"] is None


# ============================================================================
# Health Endpoints
# ============================================================================


def test_get_agent_health_not_found(client):
    """GET health for agent with no data returns 404."""
    with patch("app.main.HealthCheckRepository") as mock_repo:
        instance = mock_repo.return_value
        instance.get_health_status = AsyncMock(return_value=None)

        response = client.get(f"/agents/{MOCK_UUID}/health")

    assert response.status_code == 404


async def test_get_health_status_does_not_project_bound_param():
    """Regression for #134: GET /agents/{id}/health 500'd with asyncpg
    'inconsistent types deduced for parameter $1: uuid versus text'.

    The query bound the agent_id placeholder ($1) twice: once as a bare
    projected value (`SELECT $1 as agent_id`, inferred text) and once in
    `WHERE agent_id = $1` (inferred uuid). asyncpg cannot reconcile the two,
    so the endpoint 500'd for every agent with health rows. The fix drops the
    bare projection and returns the Python agent_id instead.

    No live Postgres in CI, so we can't trigger asyncpg's deducer directly.
    Instead we assert the structural cause is gone: the SQL must not project a
    bare placeholder, and the returned agent_id must come from the argument.
    """
    from uuid import uuid4

    from app.repositories import HealthCheckRepository

    captured = {}

    async def fake_fetchrow(query, *params):
        captured["query"] = query
        captured["params"] = params
        return {
            "is_healthy": True,
            "uptime_percentage": 100.0,
            "avg_response_time_ms": 42,
            "last_check": datetime.fromisoformat("2024-01-01T00:00:00"),
            "total_checks": 3,
            "successful_checks": 3,
        }

    db = AsyncMock()
    db.fetchrow = fake_fetchrow
    agent_id = uuid4()

    status = await HealthCheckRepository(db).get_health_status(agent_id)

    sql = " ".join(captured["query"].split())
    # The bare projection that caused the uuid-vs-text conflict must be gone.
    # An explicit cast (e.g. `$1::uuid as agent_id`) would also be acceptable,
    # so we only forbid the un-cast projection.
    assert "$1 as agent_id" not in sql.lower()
    # $1 is still bound exactly once, in the WHERE clause.
    assert sql.count("$1") == 1
    assert "where agent_id = $1" in sql.lower()
    # agent_id comes from the Python argument, not a projected row column.
    assert status is not None
    assert status.agent_id == agent_id


def test_get_agent_uptime_not_found(client):
    """GET uptime for agent with no data returns 404."""
    with patch("app.main.HealthCheckRepository") as mock_repo:
        instance = mock_repo.return_value
        instance.get_uptime_metrics = AsyncMock(return_value=None)

        response = client.get(f"/agents/{MOCK_UUID}/uptime")

    assert response.status_code == 404


def test_get_agent_uptime_period_capped(client):
    """Period_days > 90 is capped to 90."""
    with patch("app.main.HealthCheckRepository") as mock_repo:
        instance = mock_repo.return_value
        instance.get_uptime_metrics = AsyncMock(return_value=None)

        client.get(f"/agents/{MOCK_UUID}/uptime?period_days=365")

    call_args = instance.get_uptime_metrics.call_args
    assert call_args[0][1] == 90  # period_days arg


# ============================================================================
# Admin Flags (GET /admin/flags)
# ============================================================================


def test_list_flags_requires_admin(client):
    """GET /admin/flags without admin key returns 403."""
    response = client.get("/admin/flags")
    assert response.status_code == 403


def test_list_flags_success(client):
    """GET /admin/flags with admin key returns flags."""
    with patch("app.main.FlagRepository") as mock_repo, \
         patch("app.main.settings") as mock_settings:
        mock_settings.admin_api_key = "test-admin-key"
        mock_settings.rate_limit_enabled = True
        mock_settings.cors_origins = ["*"]
        instance = mock_repo.return_value
        instance.list_flags = AsyncMock(return_value=[])

        response = client.get(
            "/admin/flags",
            headers={"X-Admin-Key": "test-admin-key"},
        )

    assert response.status_code == 200
    assert response.json()["flags"] == []


# ============================================================================
# SSRF Protection
# ============================================================================


def test_ssrf_blocks_localhost():
    assert _is_private_url("http://localhost/foo") is True


def test_ssrf_blocks_private_ip():
    assert _is_private_url("http://192.168.1.1/foo") is True
    assert _is_private_url("http://10.0.0.1/foo") is True
    assert _is_private_url("http://172.16.0.1/foo") is True


def test_ssrf_blocks_loopback():
    assert _is_private_url("http://127.0.0.1/foo") is True


def test_ssrf_blocks_metadata():
    assert _is_private_url("http://metadata.google.internal/foo") is True


def test_ssrf_blocks_internal_domains():
    assert _is_private_url("http://anything.internal/foo") is True
    assert _is_private_url("http://service.local/foo") is True


def test_ssrf_blocks_kubernetes():
    assert _is_private_url("http://kubernetes.default.svc/foo") is True
    assert _is_private_url("http://my-service.namespace.svc.cluster.local/foo") is True


def test_ssrf_allows_public_urls():
    assert _is_private_url("https://example.com/foo") is False
    assert _is_private_url("https://a2aregistry.org/api") is False
    assert _is_private_url("https://api.openai.com/v1") is False


# ============================================================================
# AI Discoverability Endpoints
# ============================================================================


def test_ai_plugin_json(client):
    """/.well-known/ai-plugin.json returns valid manifest."""
    response = client.get("/.well-known/ai-plugin.json")
    assert response.status_code == 200
    body = response.json()
    assert body["name_for_model"] == "a2a_registry"
    assert "openapi" in body["api"]["type"]


def test_llms_txt(client):
    """GET /llms.txt returns plain text."""
    response = client.get("/llms.txt")
    assert response.status_code == 200
    assert "A2A Registry" in response.text
    assert "text/plain" in response.headers["content-type"]


# ============================================================================
# API Root
# ============================================================================


def test_api_root(client):
    response = client.get("/api/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "A2A Registry API"
