"""Tests for the worker's card-metadata and recovery-note refresh logic (#150, #153).

These cover the systemic gap where the health worker refreshed health and
conformance but never re-synced the *displayed* card metadata (name/version/
url/protocolVersion), so a renamed or version-bumped agent stayed frozen at its
registration values forever.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import worker
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


# ── refresh_agent_metadata ──────────────────────────────────────────────────


async def test_refresh_updates_when_name_and_version_drift():
    """The #153 scenario: live card renamed + version-bumped → record is rewritten."""
    stored = _stored_agent()
    repo = SimpleNamespace(update=AsyncMock())

    changed = await worker.refresh_agent_metadata(stored, _live_card(), repo)

    assert changed is True
    repo.update.assert_awaited_once()
    agent_id_arg, candidate = repo.update.await_args.args
    assert agent_id_arg == stored.id
    assert candidate.name == "inferGONKA"
    assert candidate.version == "1.3.0"
    assert candidate.protocolVersion == "0.3.0"
    assert str(candidate.url) == "https://a2a.gogonka.com/messages"
    # The worker must never rewrite the discovery URL.
    assert str(candidate.wellKnownURI) == stored.wellKnownURI


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
    repo = SimpleNamespace(update=AsyncMock())

    changed = await worker.refresh_agent_metadata(stored, card, repo)

    assert changed is False
    repo.update.assert_not_awaited()


async def test_refresh_normalises_snake_case_card():
    """Cards using snake_case field names (SDK style) still refresh correctly."""
    stored = _stored_agent()
    repo = SimpleNamespace(update=AsyncMock())
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
    _, candidate = repo.update.await_args.args
    assert candidate.protocolVersion == "0.3.0"
    assert candidate.version == "1.3.0"


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
