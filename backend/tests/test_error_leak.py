"""Regression tests for #140: the 500 path must not leak raw exception text.

The internal error handler and the create/update endpoints previously returned
``str(exc)`` to the client, which can disclose stack/DB internals, file paths,
and secrets on a public API. These tests assert the leaked text never reaches
the response body.
"""

from unittest.mock import AsyncMock, patch

SECRET_MARKER = "SECRET_DB_DSN=postgres://user:p4ssw0rd@10.0.0.5/registry"


def test_500_handler_does_not_leak_exception_text(client):
    """An unexpected error during create returns a generic 500, not str(exc)."""
    with (
        patch("app.main.AgentRepository") as mock_repo,
        patch("app.main.validate_well_known_uri", return_value=[]),
        patch(
            "app.main.fetch_agent_card",
            new=AsyncMock(side_effect=RuntimeError(SECRET_MARKER)),
        ),
    ):
        instance = mock_repo.return_value
        instance.get_by_well_known_uri = AsyncMock(return_value=None)
        instance.get_by_host = AsyncMock(return_value=None)
        instance.get_by_name_and_author = AsyncMock(return_value=None)

        response = client.post(
            "/agents/register",
            json={"wellKnownURI": "https://example.com/.well-known/agent.json"},
        )

    assert response.status_code == 500
    body = response.text
    assert SECRET_MARKER not in body, "raw exception text leaked into 500 response"
    assert "Internal server error" in body or "Failed to create agent" in body
    # The generic detail must be the only error signal — no `error` field echoing exc.
    payload = response.json()
    assert "error" not in payload or SECRET_MARKER not in str(payload.get("error", ""))
