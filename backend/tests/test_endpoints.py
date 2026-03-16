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
         patch("app.main.fetch_agent_card", return_value=(MOCK_AGENT_CARD, None)):
        instance = mock_repo.return_value
        instance.get_by_well_known_uri = AsyncMock(return_value=None)
        instance.get_by_host = AsyncMock(return_value=None)
        instance.create = AsyncMock(return_value=_make_agent_in_db())
        instance.get_by_id = AsyncMock(return_value=mock_public)

        response = client.post(
            "/agents/register",
            json={"wellKnownURI": "https://example.com/.well-known/agent.json"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Test Agent"


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
