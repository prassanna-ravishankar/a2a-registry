"""Tests for the worker's card-metadata and recovery-note refresh logic (#150, #153).

These cover the systemic gap where the health worker refreshed health and
conformance but never re-synced the *displayed* card metadata (name/version/
url/protocolVersion), so a renamed or version-bumped agent stayed frozen at its
registration values forever.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import worker
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


async def test_refresh_preserves_security_icon_auth_via_scoped_patch():
    """BLOCKING #2: a name/version drift must not NULL out security/icon/auth
    fields. The worker writes via the column-scoped patch, whose whitelist
    excludes those columns entirely — so they can never be touched here."""
    stored = _stored_agent()
    repo = _metadata_repo()

    await worker.refresh_agent_metadata(stored, _live_card(), repo)

    _, fields = repo.update_card_metadata.await_args.args
    for protected in ("securitySchemes", "security", "iconUrl",
                      "supportsAuthenticatedExtendedCard", "capabilities", "skills", "provider"):
        assert protected not in fields
    # And the repo whitelist itself rejects them.
    assert "security_schemes" not in AgentRepository._WORKER_REFRESHABLE_COLUMNS.values()
    assert "icon_url" not in AgentRepository._WORKER_REFRESHABLE_COLUMNS.values()


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


async def test_recovery_noop_when_not_working():
    """A still-failing probe leaves notes alone (they may carry the failure reason)."""
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
    # Columns the worker must never write must be absent from the statement.
    for forbidden in ("capabilities", "skills", "security", "security_schemes",
                      "icon_url", "supports_authenticated_extended_card",
                      "provider", "well_known_uri"):
        assert forbidden not in sql
    # Values are bound positionally; the id is the last parameter.
    assert db.execute.await_args.args[-1] == "abc"


async def test_update_card_metadata_rejects_unknown_field():
    """A non-whitelisted key is rejected loudly rather than silently widening the write."""
    db = SimpleNamespace(execute=AsyncMock())
    repo = AgentRepository(db)

    with pytest.raises(ValueError, match="not worker-refreshable"):
        await repo.update_card_metadata("abc", {"securitySchemes": {"evil": 1}})

    db.execute.assert_not_awaited()


async def test_update_card_metadata_noop_on_empty():
    """No SQL is issued when there is nothing to write."""
    db = SimpleNamespace(execute=AsyncMock())
    repo = AgentRepository(db)

    written = await repo.update_card_metadata("abc", {})

    assert written is False
    db.execute.assert_not_awaited()
