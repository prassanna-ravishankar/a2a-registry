"""#208: re-registering a listed agent refreshes it, and moves it to a new card URL
only when the URL it is registered at proves continuity."""

from unittest.mock import AsyncMock, patch

import pytest

from .conftest import MOCK_AGENT_CARD
from .test_endpoints import _make_agent_in_db, _make_agent_public

OLD_URI = "https://example.com/.well-known/agent.json"
NEW_URI = "https://new.example.org/.well-known/agent-card.json"
CARD = {**MOCK_AGENT_CARD, "url": "https://example.com/a2a"}


def _register(client, uri, *, cards, listed=None, by_host=None, by_endpoint=None, by_name=None,
              review_status=None, hidden=False):
    """POST /agents/register with `cards` mapping each fetched URL to (card, error)."""
    existing = _make_agent_public(wellKnownURI=OLD_URI, hidden=hidden)
    pick = {"listed": existing}
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.fetch_agent_card", new=AsyncMock(side_effect=lambda u: cards.get(u, (None, "unreachable")))) as fetch, \
         patch("app.main.smoke_test", new=AsyncMock(return_value=("WORKING", "ok", 10))) as probe:
        repo = mock_repo.return_value
        repo.get_by_well_known_uri = AsyncMock(return_value=pick.get(listed))
        repo.get_by_host = AsyncMock(return_value=pick.get(by_host))
        repo.get_by_endpoint_url = AsyncMock(return_value=pick.get(by_endpoint))
        repo.get_by_name_and_author = AsyncMock(return_value=pick.get(by_name))
        repo.get_review_state = AsyncMock(return_value={"review_status": review_status, "review_revision": 1})
        repo.update = AsyncMock(return_value=_make_agent_in_db())
        repo.get_by_id = AsyncMock(return_value=existing)
        repo.create = AsyncMock()
        response = client.post("/agents/register", json={"wellKnownURI": uri})
    return response, repo, fetch, probe


def test_registering_the_same_url_refreshes_the_listing(client):
    response, repo, _, probe = _register(client, OLD_URI, cards={OLD_URI: (CARD, None)}, listed="listed")
    assert response.status_code == 200, response.text
    assert str(repo.update.await_args.args[1].wellKnownURI) == OLD_URI
    repo.create.assert_not_awaited()
    probe.assert_not_awaited()


@pytest.mark.parametrize(("review_status", "hidden"), [("rejected", False), (None, True)], ids=["rejected", "deleted"])
def test_rejected_or_deleted_listings_are_not_refreshed(client, review_status, hidden):
    response, repo, _, _ = _register(client, OLD_URI, cards={OLD_URI: (CARD, None)}, listed="listed",
                                     review_status=review_status, hidden=hidden)
    assert response.status_code == 409 and "cannot be refreshed" in response.json()["detail"]
    repo.update.assert_not_awaited()


@pytest.mark.parametrize("match", ["by_host", "by_endpoint", "by_name"])
def test_a_move_is_applied_when_the_registered_url_serves_the_same_agent(client, match):
    """Andru-style: the old URL still serves (or redirects to) the same card."""
    response, repo, fetch, _ = _register(
        client, NEW_URI, cards={NEW_URI: (CARD, None), OLD_URI: (dict(CARD), None)}, **{match: "listed"},
    )
    assert response.status_code == 200, response.text
    assert str(repo.update.await_args.args[1].wellKnownURI) == NEW_URI
    assert {call.args[0] for call in fetch.await_args_list} == {NEW_URI, OLD_URI}
    repo.create.assert_not_awaited()


@pytest.mark.parametrize(
    "old",
    [(None, "unreachable"), ({**CARD, "description": "a different agent"}, None),
     ({**CARD, "url": "https://elsewhere.example/a2a"}, None)],
    ids=["old-url-dead", "different-description", "different-endpoint"],
)
def test_a_move_without_continuity_is_refused(client, old):
    """A listing cannot be taken over by registering a look-alike card elsewhere."""
    response, repo, _, probe = _register(client, NEW_URI, cards={NEW_URI: (CARD, None), OLD_URI: old},
                                         by_endpoint="listed")
    assert response.status_code == 409
    assert "already listed" in response.json()["detail"] and OLD_URI in response.json()["detail"]
    repo.update.assert_not_awaited()
    repo.create.assert_not_awaited()
    probe.assert_not_awaited()


def test_a_card_matching_two_different_listings_is_refused(client):
    other = _make_agent_public(id="11111111-1111-1111-1111-111111111111")
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.fetch_agent_card", new=AsyncMock(return_value=(CARD, None))):
        repo = mock_repo.return_value
        repo.get_by_well_known_uri = AsyncMock(return_value=None)
        repo.get_by_host = AsyncMock(return_value=None)
        repo.get_by_endpoint_url = AsyncMock(return_value=_make_agent_public())
        repo.get_by_name_and_author = AsyncMock(return_value=other)
        repo.update = AsyncMock()
        response = client.post("/agents/register", json={"wellKnownURI": NEW_URI})
    assert response.status_code == 409 and "more than one" in response.json()["detail"]
    repo.update.assert_not_awaited()
