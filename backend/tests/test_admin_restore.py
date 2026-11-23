"""#233: an admin can restore an auto-hidden agent, only while its card is reachable, and a card
that changed while hidden is reviewed before it can be public."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.card_classifier import CardVerdict, ReviewWrite

from .conftest import MOCK_AGENT_CARD
from .test_endpoints import _make_agent_in_db

AGENT = "86cb5bbc-ce0f-4eb5-9065-a15ed306dd9e"
URI = "https://pg1-ai-agent.vercel.app/.well-known/agent-card.json"


def _restore(client, *, hidden=True, card=(MOCK_AGENT_CARD, None), review=None, state_status=None,
             restored=True, updated=True, key="k"):
    order = MagicMock()
    stored = _make_agent_in_db(wellKnownURI=URI)
    state = {"review_status": state_status, "review_revision": 5, "jev_card_sha256": "old"}
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.HealthCheckRepository") as mock_health, \
         patch("app.main.fetch_agent_card", new=AsyncMock(return_value=card)) as fetch, \
         patch("app.main.assess", new=AsyncMock(return_value=review)) as assess, \
         patch("app.main.settings") as settings:
        settings.admin_api_key = "k"
        settings.jev_deadline_seconds = 45
        repo = mock_repo.return_value
        repo.get_hidden_snapshot = AsyncMock(return_value=(stored, state) if hidden else None)
        repo.restore = AsyncMock(side_effect=lambda *a, **k: (order.restore(), restored)[1])
        repo.update = AsyncMock(side_effect=lambda *a, **k: (order.update(), _make_agent_in_db() if updated else None)[1])
        health = mock_health.return_value
        health.create = AsyncMock(side_effect=lambda *a, **k: (order.health(), None)[1])
        response = client.post(f"/admin/agents/{AGENT}/restore", headers={"X-Admin-Key": key} if key else {})
    return response, repo, health, fetch, assess, order


def test_restore_requires_the_admin_key(client):
    response, _, _, fetch, _, _ = _restore(client, key=None)
    assert response.status_code == 403
    fetch.assert_not_awaited()


def test_only_a_hidden_agent_can_be_restored(client):
    response, repo, _, fetch, _, _ = _restore(client, hidden=False)
    assert response.status_code == 404
    fetch.assert_not_awaited()


def test_an_unreachable_card_stays_hidden_and_nothing_is_recorded(client):
    response, repo, health, _, assess, _ = _restore(client, card=(None, "Agent card endpoint returned HTTP 503"))
    assert response.status_code == 409 and "stays hidden" in response.json()["detail"]
    assess.assert_not_awaited()
    health.create.assert_not_awaited()
    repo.restore.assert_not_awaited()
    repo.update.assert_not_awaited()


@pytest.mark.parametrize(
    ("state_status", "public"),
    [(None, True), ("approved", True), ("flagged", True), ("pending", False), ("unscored", False), ("rejected", False)],
)
def test_unchanged_content_is_restored_as_it_was(client, state_status, public):
    response, repo, health, fetch, _, order = _restore(client, review=None, state_status=state_status)
    assert response.status_code == 200
    assert response.json() == {"id": AGENT, "hidden": False, "public": public}
    fetch.assert_awaited_once_with(URI)
    repo.restore.assert_awaited_once()
    assert repo.restore.await_args.args[1] == 5, "guarded by the snapshot revision"
    repo.update.assert_not_awaited()
    args, kwargs = health.create.await_args
    assert args[3] is True and kwargs["source"] == "admin"
    calls = [name for name, *_ in order.mock_calls if name in ("health", "restore", "update")]
    assert calls == ["health", "restore"], "success recorded before un-hiding"


@pytest.mark.parametrize(("verdict_status", "public"), [(None, True), ("pending", False), ("unscored", False)])
def test_a_card_changed_while_hidden_is_reviewed_before_it_can_be_public(client, verdict_status, public):
    """#235 review P1: changed content is classified, then written with its review in the
    same statement that un-hides it; a flagged or unscorable card comes back held."""
    verdict = CardVerdict(score=0.9 if verdict_status else 0.1, signals={}, model="jev-test")
    review = ReviewWrite(verdict=verdict, sha="new", status=verdict_status, expect_revision=5)
    response, repo, _, _, assess, _ = _restore(client, review=review)
    assert response.status_code == 200 and response.json()["public"] is public
    assess.assert_awaited_once()
    repo.update.assert_awaited_once()
    assert repo.update.await_args.kwargs == {"review": review, "unhide": True}
    repo.restore.assert_not_awaited()


@pytest.mark.parametrize("path", ["unchanged", "changed"])
def test_a_retire_in_between_wins(client, path):
    """#235 review P2: the guarded write is refused if the agent changed since the snapshot."""
    review = None if path == "unchanged" else ReviewWrite(
        verdict=CardVerdict(score=0.1, signals={}, model="jev-test"), sha="new", status=None, expect_revision=5,
    )
    response, _, _, _, _, _ = _restore(client, review=review, restored=False, updated=False)
    assert response.status_code == 409 and "changed while it was being restored" in response.json()["detail"]
