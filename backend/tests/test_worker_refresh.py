"""Tests for the worker's card-metadata and recovery-note refresh logic (#150, #153).

These cover the systemic gap where the health worker refreshed health and
conformance but never re-synced the *displayed* card metadata (name/version/
url/protocolVersion), so a renamed or version-bumped agent stayed frozen at its
registration values forever.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import worker
from app.agent_card import agent_create_from_card
from app.models import Skill
from app.repositories import AgentRepository
from app.smoke_test import CATEGORY_NOTES


def _stored_agent(**overrides):
    """A minimal stand-in for the stored AgentPublic record the worker reads.

    Only the attributes the refresh helpers touch are populated.
    """
    base = dict(
        id="95e89fba-1765-4c16-a8c5-0a239dbfd29e",
        name="Gonka Cost Optimizer",
        version="1.1.0",
        url="https://a2a.gogonka.com/",
        protocolVersion="unknown",
        description="old description",
        author="Gonka",
        wellKnownURI="https://a2a.gogonka.com/.well-known/agent.json",
        maintainer_notes=None,
        provider=None,
        security=[],
        securitySchemes={},
        documentationUrl=None,
        iconUrl=None,
        supportsAuthenticatedExtendedCard=None,
        capabilities={
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain"],
        skills=[],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _live_card(**overrides):
    card = {
        "protocolVersion": "0.3.0",
        "name": "inferGONKA",
        "description": "Spend less. Build more.",
        "url": "https://a2a.gogonka.com/messages",
        "version": "1.3.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [],
    }
    card.update(overrides)
    return card


def _live_card_v1(iface_url="https://new.example/messages", iface_proto="1.0", **overrides):
    """A v1.0-shaped card: no top-level url/protocolVersion; both live nested in
    interfaces[0]. _normalise_fields lifts them to top level for value extraction,
    but presence must be detected from this raw nested shape."""
    card = {
        "name": "inferGONKA",
        "description": "Spend less. Build more.",
        "version": "1.3.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [],
        "interfaces": [{"url": iface_url, "protocolVersion": iface_proto}],
    }
    card.update(overrides)
    return card


def test_registration_model_preserves_auth_declarations():
    card = _live_card(
        security=[{"apiKey": []}],
        securitySchemes={"apiKey": {"type": "apiKey", "in": "header", "name": "x-api-key"}},
    )

    agent = agent_create_from_card(
        card, "https://example.com/.well-known/agent-card.json"
    )

    assert agent.security == [{"apiKey": []}]
    assert agent.securitySchemes["apiKey"]["name"] == "x-api-key"


def test_registration_model_normalises_v1_security_and_extended_card():
    card = _live_card_v1(
        securityRequirements=[{"apiKey": []}],
        securitySchemes={"apiKey": {"type": "apiKey", "in": "header"}},
        capabilities={"streaming": False, "extendedAgentCard": True},
    )

    agent = agent_create_from_card(
        card, "https://example.com/.well-known/agent-card.json"
    )

    assert agent.security == [{"apiKey": []}]
    assert agent.supportsAuthenticatedExtendedCard is True


# ── refresh_agent_metadata ──────────────────────────────────────────────────


def _metadata_repo():
    """Repo stub for metadata refresh. update_card_metadata returns True (a row
    was updated); the full-record update() must NEVER be called by the worker."""
    return SimpleNamespace(
        update_card_metadata=AsyncMock(return_value=True),
        update=AsyncMock(),
    )


async def test_refresh_updates_when_name_and_version_drift():
    """The #153 scenario: live card renamed + version-bumped → displayed fields patched."""
    stored = _stored_agent()
    repo = _metadata_repo()

    changed = await worker.refresh_agent_metadata(stored, _live_card(), repo)

    assert changed is True
    # Must use the column-scoped patch, never the full-record update().
    repo.update.assert_not_awaited()
    repo.update_card_metadata.assert_awaited_once()
    agent_id_arg, fields = repo.update_card_metadata.await_args.args
    assert agent_id_arg == stored.id
    assert fields["name"] == "inferGONKA"
    assert fields["version"] == "1.3.0"
    assert fields["protocolVersion"] == "0.3.0"
    assert fields["url"] == "https://a2a.gogonka.com/messages"
    # Only the displayed whitelist is ever written — nothing else.
    assert set(fields).issubset(set(worker._REFRESHED_FIELDS))


async def test_refresh_only_writes_changed_fields():
    """A pure rename patches only `name`, leaving unchanged fields out of the write."""
    card = _live_card()
    stored = _stored_agent(
        name="Old Name",
        version=card["version"],
        url=card["url"],
        protocolVersion=card["protocolVersion"],
        description=card["description"],
    )
    repo = _metadata_repo()

    changed = await worker.refresh_agent_metadata(stored, card, repo)

    assert changed is True
    _, fields = repo.update_card_metadata.await_args.args
    assert fields == {"name": "inferGONKA"}


async def test_refresh_noop_when_card_matches_stored():
    """No write (and no updated_at churn) when nothing drifted."""
    card = _live_card()
    stored = _stored_agent(
        name=card["name"],
        version=card["version"],
        url=card["url"],
        protocolVersion=card["protocolVersion"],
        description=card["description"],
    )
    repo = _metadata_repo()

    changed = await worker.refresh_agent_metadata(stored, card, repo)

    assert changed is False
    repo.update_card_metadata.assert_not_awaited()


async def test_refresh_rejects_object_valued_skill_examples():
    stored = _stored_agent()
    repo = _metadata_repo()
    card = _live_card(
        skills=[{
            "id": "probe",
            "name": "Probe",
            "description": "Probe an endpoint",
            "examples": [{"name": "not a valid A2A example"}],
        }]
    )

    changed = await worker.refresh_agent_metadata(stored, card, repo)

    assert changed is False
    repo.update_card_metadata.assert_not_awaited()


async def test_health_loader_isolates_malformed_legacy_rows():
    good_id = "95e89fba-1765-4c16-a8c5-0a239dbfd29e"
    bad_id = "c6d8a87e-f439-4a4e-a42c-6cbb9037207e"
    good_agent = _stored_agent(id=good_id)
    fake_db = SimpleNamespace(
        fetch=AsyncMock(return_value=[{"id": good_id}, {"id": bad_id}])
    )
    repo = AgentRepository(fake_db)
    repo._row_to_agent = Mock(side_effect=[good_agent, ValueError("untrusted payload")])

    agents, invalid_ids = await repo.list_agents_for_health_checks()

    assert agents == [good_agent]
    assert invalid_ids == [bad_id]
    fake_db.fetch.assert_awaited_once_with(
        "SELECT * FROM agents WHERE hidden = false ORDER BY created_at DESC"
    )


def test_comparable_handles_model_objects_nested_in_lists():
    skill_model = Skill(
        id="onboarding",
        name="Get started",
        description="Register an account.",
        tags=["onboarding"],
    )
    skill_dict = skill_model.model_dump(mode="json", exclude_none=True)

    assert worker._comparable([skill_model]) == worker._comparable([skill_dict])


async def test_refresh_normalises_snake_case_card():
    """Cards using snake_case field names (SDK style) still refresh correctly."""
    stored = _stored_agent()
    repo = _metadata_repo()
    snake_card = {
        "protocol_version": "0.3.0",
        "name": "inferGONKA",
        "description": "x",
        "url": "https://a2a.gogonka.com/messages",
        "version": "1.3.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
        "default_input_modes": ["text/plain"],
        "default_output_modes": ["text/plain"],
        "skills": [],
    }

    changed = await worker.refresh_agent_metadata(stored, snake_card, repo)

    assert changed is True
    _, fields = repo.update_card_metadata.await_args.args
    assert fields["protocolVersion"] == "0.3.0"
    assert fields["version"] == "1.3.0"


# ── data-integrity guards (PR #154 review: blocking findings) ────────────────


async def test_refresh_card_missing_version_never_clobbers_with_default():
    """BLOCKING #1: a card missing `version` must NOT overwrite the stored version
    with a default ('1.0.0').

    Note: the registry's strict validator does NOT require `version`, so the
    strict gate alone wouldn't catch this — the real safeguard is that the field
    extractor omits absent fields entirely. Here the card matches the stored
    record on everything *except* the (absent) version, so the write is empty."""
    card = _live_card()
    stored = _stored_agent(
        name=card["name"],
        version="1.1.0",  # stored has a real version
        url=card["url"],
        protocolVersion=card["protocolVersion"],
        description=card["description"],
    )
    del card["version"]  # live card dropped its version
    repo = _metadata_repo()

    changed = await worker.refresh_agent_metadata(stored, card, repo)

    assert changed is False  # version omitted, nothing else drifted
    repo.update_card_metadata.assert_not_awaited()
    repo.update.assert_not_awaited()


async def test_refresh_present_field_extraction_never_synthesises_version():
    """Defence-in-depth for BLOCKING #1: when other fields drift but `version` is
    absent from the card, the extractor omits `version` rather than supplying a
    default — so the stored version survives while the real change is written."""
    stored = _stored_agent(version="1.1.0", name="Old Name")
    repo = _metadata_repo()
    card = _live_card()
    del card["version"]

    changed = await worker.refresh_agent_metadata(stored, card, repo)

    assert changed is True  # name changed
    _, fields = repo.update_card_metadata.await_args.args
    assert "version" not in fields  # never synthesised
    assert fields["name"] == "inferGONKA"


async def test_refresh_updates_explicit_card_fields_via_scoped_patch():
    """Strict-valid, explicitly present Agent Card fields stay current."""
    stored = _stored_agent(
        documentationUrl="https://old.example/docs",
        iconUrl="https://old.example/icon.png",
        skills=[{"id": "old"}],
    )
    repo = _metadata_repo()
    card = _live_card(
        documentationUrl="https://new.example/docs",
        iconUrl="https://new.example/icon.png",
        capabilities={"streaming": True, "extendedAgentCard": True},
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
        skills=[
            {
                "id": "onboarding",
                "name": "Get started",
                "description": "Register an account.",
                "tags": ["onboarding"],
            }
        ],
    )

    await worker.refresh_agent_metadata(stored, card, repo)

    _, fields = repo.update_card_metadata.await_args.args
    assert fields["documentationUrl"] == "https://new.example/docs"
    assert fields["iconUrl"] == "https://new.example/icon.png"
    assert fields["supportsAuthenticatedExtendedCard"] is True
    assert fields["capabilities"]["streaming"] is True
    assert "extendedAgentCard" not in fields["capabilities"]
    assert fields["defaultInputModes"] == ["application/json"]
    assert fields["defaultOutputModes"] == ["application/json"]
    assert fields["skills"][0]["id"] == "onboarding"


async def test_refresh_absent_optional_card_fields_preserve_stored_values():
    stored = _stored_agent(
        documentationUrl="https://existing.example/docs",
        iconUrl="https://existing.example/icon.png",
        supportsAuthenticatedExtendedCard=True,
    )
    repo = _metadata_repo()

    await worker.refresh_agent_metadata(stored, _live_card(), repo)

    _, fields = repo.update_card_metadata.await_args.args
    assert not {
        "documentationUrl",
        "iconUrl",
        "supportsAuthenticatedExtendedCard",
    } & fields.keys()


async def test_refresh_updates_provider_and_security_when_declared():
    stored = _stored_agent()
    repo = _metadata_repo()
    card = _live_card(
        provider={"organization": "Cog Depot", "url": "https://cogdepot.com"},
        security=[{"apiKey": []}],
        securitySchemes={
            "apiKey": {"type": "apiKey", "in": "header", "name": "x-api-key"}
        },
    )

    changed = await worker.refresh_agent_metadata(stored, card, repo)

    assert changed is True
    _, fields = repo.update_card_metadata.await_args.args
    assert fields["provider"]["organization"] == "Cog Depot"
    assert fields["security"] == [{"apiKey": []}]
    assert fields["securitySchemes"]["apiKey"]["name"] == "x-api-key"


async def test_refresh_absent_auth_fields_do_not_clear_stored_values():
    stored = _stored_agent(
        provider={"organization": "Existing"},
        security=[{"oauth": []}],
        securitySchemes={"oauth": {"type": "oauth2"}},
    )
    repo = _metadata_repo()

    await worker.refresh_agent_metadata(stored, _live_card(), repo)

    _, fields = repo.update_card_metadata.await_args.args
    assert not {"provider", "security", "securitySchemes"} & fields.keys()


async def test_refresh_skips_non_conformant_card():
    """BLOCKING #1: a degraded-but-parseable card (strict conformance errors)
    must not refresh displayed metadata at all."""
    stored = _stored_agent()
    repo = _metadata_repo()

    changed = await worker.refresh_agent_metadata(
        stored, _live_card(), repo, conformance_errors=["some strict error"],
    )

    assert changed is False
    repo.update_card_metadata.assert_not_awaited()


async def test_refresh_no_churn_on_bare_host_url_trailing_slash():
    """A card url of 'https://x.com' must not rewrite the stored 'https://x.com/'
    every cycle. The candidate url is canonicalised to HttpUrl form, matching how
    the stored value round-trips, so no spurious diff occurs."""
    card = _live_card(url="https://example.com")  # no trailing slash on the card
    stored = _stored_agent(
        name=card["name"],
        version=card["version"],
        url="https://example.com/",  # stored as HttpUrl renders it
        protocolVersion=card["protocolVersion"],
        description=card["description"],
    )
    repo = _metadata_repo()

    changed = await worker.refresh_agent_metadata(stored, card, repo)

    assert changed is False
    repo.update_card_metadata.assert_not_awaited()


async def test_refresh_skips_unknown_protocol_version_sentinel():
    """A card with no protocolVersion (extractor returns 'unknown') must not
    overwrite a stored real protocolVersion with the sentinel."""
    stored = _stored_agent(protocolVersion="0.3.0", name="Old Name")
    repo = _metadata_repo()
    card = _live_card()
    del card["protocolVersion"]

    # Without protocolVersion the card fails strict validation, so force the gate
    # open to isolate the sentinel guard.
    changed = await worker.refresh_agent_metadata(
        stored, card, repo, conformance_errors=[],
    )

    assert changed is True  # name changed
    _, fields = repo.update_card_metadata.await_args.args
    assert "protocolVersion" not in fields


# ── v1.0 nested-interface presence (PR #154 re-review: still-blocking) ───────


async def test_refresh_v1_interface_only_url_and_protocol_drift_refreshes():
    """STILL-BLOCKING: a strict-valid v1.0 card whose url + protocolVersion live
    ONLY in interfaces[0] must still refresh when they drift. Presence detection
    has to look inside the nested interface, not just top-level string keys."""
    stored = _stored_agent(
        url="https://old.example/messages",
        protocolVersion="0.3.0",
        # name/version/description match so the ONLY drift is the nested fields.
        name="inferGONKA",
        version="1.3.0",
        description="Spend less. Build more.",
    )
    repo = _metadata_repo()
    card = _live_card_v1(iface_url="https://new.example/messages", iface_proto="1.0")

    changed = await worker.refresh_agent_metadata(stored, card, repo)

    assert changed is True
    repo.update.assert_not_awaited()
    _, fields = repo.update_card_metadata.await_args.args
    assert fields["url"] == "https://new.example/messages"
    assert fields["protocolVersion"] == "1.0"
    # Only the nested fields drifted, so only those are written.
    assert set(fields) == {"url", "protocolVersion"}


async def test_refresh_v1_interface_missing_nested_values_writes_no_sentinel():
    """A v1.0 card whose interface lacks url/protocolVersion (and has only a
    top-level url) must not write the 'unknown' protocolVersion sentinel, and
    must not blank a stored url it can't re-derive."""
    stored = _stored_agent(
        url="https://top.example/x",
        protocolVersion="0.3.0",
        name="Old Name",  # force a real change so a write happens at all
        version="1.3.0",
        description="Spend less. Build more.",
    )
    repo = _metadata_repo()
    card = {
        "name": "inferGONKA",
        "description": "Spend less. Build more.",
        "version": "1.3.0",
        "url": "https://top.example/x",  # top-level url present (unchanged)
        "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [],
        "interfaces": [{"transport": "JSONRPC"}],  # no url, no protocolVersion
    }

    changed = await worker.refresh_agent_metadata(stored, card, repo)

    assert changed is True  # name changed
    _, fields = repo.update_card_metadata.await_args.args
    assert fields == {"name": "inferGONKA"}
    assert "protocolVersion" not in fields  # never the 'unknown' sentinel


# ── refresh_recovery_notes ──────────────────────────────────────────────────


async def test_recovery_clears_stale_system_failure_note():
    """The #150/#153 stale-notes contradiction: a system 404 note is replaced on recovery."""
    stored = _stored_agent(maintainer_notes=CATEGORY_NOTES["404"])
    repo = SimpleNamespace(update_maintainer_notes=AsyncMock())

    changed = await worker.refresh_recovery_notes(stored, "WORKING", repo)

    assert changed is True
    repo.update_maintainer_notes.assert_awaited_once_with(stored.id, CATEGORY_NOTES["WORKING"])


async def test_recovery_preserves_human_authored_notes():
    """A human-written note must never be overwritten by the worker."""
    stored = _stored_agent(maintainer_notes="Hand-written note from the maintainer.")
    repo = SimpleNamespace(update_maintainer_notes=AsyncMock())

    changed = await worker.refresh_recovery_notes(stored, "WORKING", repo)

    assert changed is False
    repo.update_maintainer_notes.assert_not_awaited()


async def test_system_note_tracks_transition_between_failure_categories():
    stored = _stored_agent(maintainer_notes=CATEGORY_NOTES["404"])
    repo = SimpleNamespace(update_maintainer_notes=AsyncMock())

    changed = await worker.refresh_recovery_notes(stored, "401", repo)

    assert changed is True
    repo.update_maintainer_notes.assert_awaited_once_with(stored.id, CATEGORY_NOTES["401"])


async def test_legacy_system_note_updates_to_current_category_wording():
    legacy_note = (
        "Agent's gRPC/protobuf response includes a field not defined in the A2A "
        "schema. Align response with the latest A2A spec."
    )
    stored = _stored_agent(maintainer_notes=legacy_note)
    repo = SimpleNamespace(update_maintainer_notes=AsyncMock())

    changed = await worker.refresh_recovery_notes(stored, "PARSE", repo)

    assert changed is True
    repo.update_maintainer_notes.assert_awaited_once_with(
        stored.id, CATEGORY_NOTES["PARSE"]
    )


async def test_system_note_noop_when_failure_category_matches():
    stored = _stored_agent(maintainer_notes=CATEGORY_NOTES["404"])
    repo = SimpleNamespace(update_maintainer_notes=AsyncMock())

    changed = await worker.refresh_recovery_notes(stored, "404", repo)

    assert changed is False
    repo.update_maintainer_notes.assert_not_awaited()


async def test_recovery_noop_when_already_working_note():
    """No redundant write when the note is already the WORKING note."""
    stored = _stored_agent(maintainer_notes=CATEGORY_NOTES["WORKING"])
    repo = SimpleNamespace(update_maintainer_notes=AsyncMock())

    changed = await worker.refresh_recovery_notes(stored, "WORKING", repo)

    assert changed is False
    repo.update_maintainer_notes.assert_not_awaited()


async def test_recovery_noop_when_no_notes():
    """Empty notes need no change."""
    stored = _stored_agent(maintainer_notes=None)
    repo = SimpleNamespace(update_maintainer_notes=AsyncMock())

    changed = await worker.refresh_recovery_notes(stored, "WORKING", repo)

    assert changed is False
    repo.update_maintainer_notes.assert_not_awaited()


# ── AgentRepository.update_card_metadata (column-scoped patch) ────────────────


async def test_update_card_metadata_writes_only_whitelisted_columns():
    """The patch SQL touches only the mapped columns + updated_at, never the
    full card. This is the structural guarantee behind PR #154 BLOCKING #2."""
    db = SimpleNamespace(execute=AsyncMock(return_value="UPDATE 1"))
    repo = AgentRepository(db)

    written = await repo.update_card_metadata(
        "abc", {"name": "New", "version": "2.0.0", "protocolVersion": "0.3.0"}
    )

    assert written is True
    sql = db.execute.await_args.args[0]
    assert "name = $1" in sql and "version = $2" in sql and "protocol_version = $3" in sql
    assert "updated_at = NOW()" in sql
    # Registry-owned columns remain outside the worker patch surface.
    for forbidden in ("well_known_uri", "author", "license", "pricing", "contact"):
        assert forbidden not in sql
    # Values are bound positionally; the id is the last parameter.
    assert db.execute.await_args.args[-1] == "abc"


async def test_update_card_metadata_rejects_unknown_field():
    """A non-whitelisted key is rejected loudly rather than silently widening the write."""
    db = SimpleNamespace(execute=AsyncMock())
    repo = AgentRepository(db)

    with pytest.raises(ValueError, match="not worker-refreshable"):
        await repo.update_card_metadata("abc", {"license": "MIT"})

    db.execute.assert_not_awaited()


async def test_update_card_metadata_serialises_auth_json_fields():
    db = SimpleNamespace(execute=AsyncMock(return_value="UPDATE 1"))
    repo = AgentRepository(db)

    written = await repo.update_card_metadata(
        "abc",
        {
            "provider": {"organization": "Cog Depot"},
            "security": [{"apiKey": []}],
            "securitySchemes": {"apiKey": {"type": "apiKey"}},
        },
    )

    assert written is True
    sql, provider, security, schemes, agent_id = db.execute.await_args.args
    assert "provider = $1" in sql
    assert "security_requirements = $2" in sql
    assert "security_schemes = $3" in sql
    assert json.loads(provider) == {"organization": "Cog Depot"}
    assert json.loads(security) == [{"apiKey": []}]
    assert json.loads(schemes) == {"apiKey": {"type": "apiKey"}}
    assert agent_id == "abc"


async def test_update_card_metadata_serialises_display_card_fields():
    db = SimpleNamespace(execute=AsyncMock(return_value="UPDATE 1"))
    repo = AgentRepository(db)

    written = await repo.update_card_metadata(
        "abc",
        {
            "documentationUrl": "https://example.com/docs",
            "capabilities": {"streaming": True},
            "defaultInputModes": ["application/json"],
            "skills": [{"id": "onboarding"}],
        },
    )

    assert written is True
    sql, documentation_url, capabilities, input_modes, skills, agent_id = (
        db.execute.await_args.args
    )
    assert "documentation_url = $1" in sql
    assert "capabilities = $2" in sql
    assert "default_input_modes = $3" in sql
    assert "skills = $4" in sql
    assert documentation_url == "https://example.com/docs"
    assert json.loads(capabilities) == {"streaming": True}
    assert json.loads(input_modes) == ["application/json"]
    assert json.loads(skills) == [{"id": "onboarding"}]
    assert agent_id == "abc"


async def test_update_card_metadata_noop_on_empty():
    """No SQL is issued when there is nothing to write."""
    db = SimpleNamespace(execute=AsyncMock())
    repo = AgentRepository(db)

    written = await repo.update_card_metadata("abc", {})

    assert written is False
    db.execute.assert_not_awaited()
