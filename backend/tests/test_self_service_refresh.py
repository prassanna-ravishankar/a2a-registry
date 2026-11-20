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
              review_status=None, hidden=False, update_result="written"):
    """POST /agents/register with `cards` mapping each fetched URL to (card, error)."""
    existing = _make_agent_public(wellKnownURI=OLD_URI, hidden=hidden)
    stored = _make_agent_in_db(wellKnownURI=OLD_URI)
    pick = {"listed": existing}
    with patch("app.main.AgentRepository") as mock_repo, \
         patch("app.main.fetch_agent_card", new=AsyncMock(side_effect=lambda u: cards.get(u, (None, "unreachable")))) as fetch, \
         patch("app.main.smoke_test", new=AsyncMock(return_value=("WORKING", "ok", 10))) as probe:
        repo = mock_repo.return_value
        repo.get_by_well_known_uri = AsyncMock(return_value=pick.get(listed))
        repo.get_by_host = AsyncMock(return_value=pick.get(by_host))
        repo.get_by_endpoint_url = AsyncMock(return_value=pick.get(by_endpoint))
        repo.get_by_name_and_author = AsyncMock(return_value=pick.get(by_name))
        # The paired snapshot hides deleted listings, as get_review_snapshot does.
        repo.get_review_snapshot = AsyncMock(
            return_value=None if hidden else (stored, {"review_status": review_status, "review_revision": 7}),
        )
        repo.update = AsyncMock(return_value=_make_agent_in_db() if update_result == "written" else None)
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
    response, repo, fetch, _ = _register(client, OLD_URI, cards={OLD_URI: (CARD, None)}, listed="listed",
                                         review_status=review_status, hidden=hidden)
    assert response.status_code == 409 and "cannot be refreshed" in response.json()["detail"]
    fetch.assert_not_awaited()  # refused before any outbound work
    repo.update.assert_not_awaited()


def test_the_write_is_guarded_by_the_snapshot_the_authority_came_from(client):
    """#232 review: if the listing changed after the snapshot, the guarded write is
    refused rather than rolling it back to stale content."""
    response, repo, _, _ = _register(client, OLD_URI, cards={OLD_URI: ({**CARD, "version": "9.9.9"}, None)},
                                     listed="listed", update_result="refused")
    assert response.status_code == 409 and "changed while it was being reviewed" in response.json()["detail"]
    assert repo.update.await_args.kwargs["review"].expect_revision == 7


# The card at the registered URL now points its endpoint at new.example.org.
MOVED_CARD = {**CARD, "url": "https://new.example.org/a2a"}


@pytest.mark.parametrize("match", ["by_host", "by_endpoint", "by_name"])
def test_a_move_to_the_root_card_of_the_endpoint_host_is_applied(client, match):
    """The registered card names new.example.org as its endpoint, so the root card there
    is the operator's, even when the two cards differ (HumanMirror's version drift)."""
    response, repo, fetch, _ = _register(
        client, NEW_URI, cards={NEW_URI: ({**MOVED_CARD, "version": "2.0.0"}, None), OLD_URI: (MOVED_CARD, None)},
        **{match: "listed"},
    )
    assert response.status_code == 200, response.text
    assert str(repo.update.await_args.args[1].wellKnownURI) == NEW_URI
    assert {call.args[0] for call in fetch.await_args_list} == {NEW_URI, OLD_URI}
    repo.create.assert_not_awaited()


def test_a_copy_of_someones_card_on_another_host_cannot_move_their_listing(client):
    """#232 review: an attacker serves a byte-identical copy of the victim's public card.
    The victim's own card still names the victim's endpoint host, so nothing moves."""
    attacker_uri = "https://evil.example/.well-known/agent-card.json"
    response, repo, _, probe = _register(
        client, attacker_uri, cards={attacker_uri: (CARD, None), OLD_URI: (CARD, None)}, by_endpoint="listed",
    )
    assert response.status_code == 409 and "already listed" in response.json()["detail"]
    repo.update.assert_not_awaited()
    repo.create.assert_not_awaited()
    probe.assert_not_awaited()


@pytest.mark.parametrize(
    ("new_uri", "old", "code"),
    [
        (NEW_URI, (None, "unreachable"), 409),
        ("https://new.example.org/tenants/b/.well-known/agent-card.json", (MOVED_CARD, None), 409),
        # /register's own path rule refuses a query string before the move check.
        ("https://new.example.org/.well-known/agent-card.json?v=1", (MOVED_CARD, None), 400),
        ("https://new.example.org:8443/.well-known/agent-card.json", (MOVED_CARD, None), 409),
        (NEW_URI, ({**MOVED_CARD, "url": "http://new.example.org/a2a"}, None), 409),
    ],
    ids=["registered-url-dead", "non-root-path", "query", "non-default-port", "plain-http-endpoint"],
)
def test_a_move_without_continuity_is_refused(client, new_uri, old, code):
    response, repo, _, _ = _register(client, new_uri, cards={new_uri: (MOVED_CARD, None), OLD_URI: old},
                                     by_endpoint="listed")
    assert response.status_code == code
    if code == 409:
        assert "already listed" in response.json()["detail"] and OLD_URI in response.json()["detail"]
    repo.update.assert_not_awaited()


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



def test_a_listing_found_only_by_its_endpoint_is_charged_as_a_refresh(client):
    """#232 review: the per-listing cap holds however the listing is reached."""
    from app.rate_limits import refresh_limits

    with patch("app.main.take", new=AsyncMock()) as take:
        _register(client, NEW_URI, cards={NEW_URI: (MOVED_CARD, None), OLD_URI: (MOVED_CARD, None)},
                  by_endpoint="listed")
    charged = [call.args[1] for call in take.await_args_list]
    assert refresh_limits(str(_make_agent_public().id)) in charged
