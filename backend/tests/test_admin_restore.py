"""#233: an admin can restore an auto-hidden agent, only while its card is reachable."""

from unittest.mock import AsyncMock, patch

import pytest

from .conftest import MOCK_AGENT_CARD

AGENT = "86cb5bbc-ce0f-4eb5-9065-a15ed306dd9e"
URI = "https://pg1-ai-agent.vercel.app/.well-known/agent-card.json"


def _restore(client, *, hidden_uri=URI, card=(MOCK_AGENT_CARD, None), restored=True, review_status=None, key="k"):
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.HealthCheckRepository") as mock_health, \
         patch("app.main.fetch_agent_card", new=AsyncMock(return_value=card)) as fetch, \
         patch("app.main.settings") as settings:
        settings.admin_api_key = "k"
        repo = mock_repo.return_value
        repo.get_hidden_card_uri = AsyncMock(return_value=hidden_uri)
        repo.restore = AsyncMock(return_value=restored)
        repo.get_review_state = AsyncMock(return_value={"review_status": review_status})
        health = mock_health.return_value
        health.create = AsyncMock()
        response = client.post(f"/admin/agents/{AGENT}/restore", headers={"X-Admin-Key": key} if key else {})
    return response, repo, health, fetch


def test_restore_requires_the_admin_key(client):
    response, repo, _, fetch = _restore(client, key=None)
    assert response.status_code == 403
    fetch.assert_not_awaited()


def test_only_a_hidden_agent_can_be_restored(client):
    response, repo, _, fetch = _restore(client, hidden_uri=None)
    assert response.status_code == 404
    fetch.assert_not_awaited()
    repo.restore.assert_not_awaited()


def test_an_unreachable_card_stays_hidden_and_nothing_is_recorded(client):
    response, repo, health, _ = _restore(client, card=(None, "Agent card endpoint returned HTTP 503"))
    assert response.status_code == 409 and "stays hidden" in response.json()["detail"]
    health.create.assert_not_awaited()
    repo.restore.assert_not_awaited()


@pytest.mark.parametrize(("review_status", "public"), [(None, True), ("approved", True), ("pending", False),
                                                     ("rejected", False)])
def test_a_reachable_card_is_recorded_healthy_then_restored(client, review_status, public):
    """The success row keeps the dead-agent rule from re-hiding it before the worker's next check;
    moderation decides public visibility as before."""
    response, repo, health, fetch = _restore(client, review_status=review_status)
    assert response.status_code == 200
    assert response.json() == {"id": AGENT, "hidden": False, "public": public}
    fetch.assert_awaited_once_with(URI)
    args, kwargs = health.create.await_args
    assert args[3] is True and kwargs["source"] == "admin"
    repo.restore.assert_awaited_once()
