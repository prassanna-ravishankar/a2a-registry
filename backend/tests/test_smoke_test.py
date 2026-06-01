"""Tests for the registration-time smoke-test classifier."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.smoke_test import (
    CATEGORY_NOTES,
    HARD_REJECT_CATEGORIES,
    classify_error,
    rejection_message,
    should_reject,
    smoke_test,
)

# Upper bound of a PostgreSQL INTEGER (int32). agents.task_conformance_response_ms
# is declared INTEGER, so smoke_test()'s response_ms must fit or asyncpg rejects
# the write with "value out of int32 range".
PG_INT32_MAX = 2_147_483_647


def _exc(name: str, msg: str) -> BaseException:
    """Build a one-off exception with a custom class name for classifier tests."""
    cls = type(name, (Exception,), {})
    return cls(msg)


def test_classify_404():
    assert classify_error(_exc("A2AClientError", "HTTP Error: 404")) == "404"
    assert classify_error(_exc("A2AClientError", "HTTP Error 404: Client error '404 Not Found'")) == "404"


def test_classify_405_401_403_400_402():
    assert classify_error(_exc("A2AClientError", "HTTP Error: 405")) == "405"
    assert classify_error(_exc("A2AClientError", "HTTP Error: 401")) == "401"
    assert classify_error(_exc("A2AClientError", "HTTP Error: 403")) == "403"
    assert classify_error(_exc("A2AClientError", "HTTP Error: 400")) == "400"
    assert classify_error(_exc("A2AClientError", "HTTP Error: 402")) == "402"


def test_classify_no_transports():
    assert classify_error(ValueError("no compatible transports found.")) == "NO_TRANSPORTS"


def test_classify_dns():
    assert classify_error(
        _exc("AgentCardResolutionError", "Network communication error fetching agent card")
    ) == "DNS"
    assert classify_error(
        _exc("AgentCardResolutionError", "[Errno 8] nodename nor servname provided, or not known")
    ) == "DNS"


def test_classify_version():
    assert classify_error(_exc("VersionNotSupportedError", "A2A version '0.3' is not supported")) == "VERSION"


def test_classify_bad_response():
    assert classify_error(ValueError("Response has neither task nor message")) == "BAD_RESPONSE"
    assert classify_error(ValueError("Either result or error should be used")) == "BAD_RESPONSE"


def test_classify_bad_json():
    assert classify_error(_exc("A2AClientError", "JSON Decode Error: Expecting value")) == "BAD_JSON"


def test_classify_method_not_found():
    assert classify_error(_exc("MethodNotFoundError", "Unknown method: message/send")) == "METHOD"


def test_classify_parse_error():
    assert classify_error(_exc("ParseError", 'Message type has no field named "id"')) == "PARSE"


def test_classify_internal_auth_backend():
    assert classify_error(
        _exc("InternalError", "Error code: 401 - {'type': 'authentication_error'}")
    ) == "AUTH_BACKEND"


def test_classify_internal_generic():
    assert classify_error(_exc("InternalError", "Internal error")) == "INTERNAL"


def test_classify_timeout():
    assert classify_error(_exc("TimeoutError", "timeout")) == "TIMEOUT"
    assert classify_error(_exc("ReadTimeout", "read timeout")) == "TIMEOUT"


def test_classify_unknown_falls_back_to_other():
    assert classify_error(RuntimeError("something weird happened")) == "OTHER"


def test_should_reject_no_transports_and_version():
    assert should_reject("NO_TRANSPORTS")
    assert should_reject("VERSION")
    assert HARD_REJECT_CATEGORIES == frozenset({"NO_TRANSPORTS", "VERSION"})
    for cat in ("WORKING", "404", "405", "401", "DNS", "BAD_RESPONSE", "TIMEOUT", "OTHER"):
        assert not should_reject(cat), f"{cat} should not be hard-rejected"


def test_rejection_message_returns_note_for_rejected():
    assert rejection_message("NO_TRANSPORTS") == CATEGORY_NOTES["NO_TRANSPORTS"]
    assert rejection_message("VERSION") == CATEGORY_NOTES["VERSION"]
    assert rejection_message("404") is None


def test_every_category_has_a_note():
    for cat in (
        "WORKING", "NO_TRANSPORTS", "404", "405", "401", "403", "402", "400",
        "DNS", "VERSION", "BAD_RESPONSE", "BAD_JSON", "METHOD", "PARSE",
        "AUTH_BACKEND", "INTERNAL", "TIMEOUT", "OTHER",
    ):
        assert cat in CATEGORY_NOTES
        assert CATEGORY_NOTES[cat]


# --- smoke_test() timing regression ----------------------------------------
#
# smoke_test() once started its timer with time.monotonic() but measured the
# elapsed time with time.time(). Those clocks have different epochs, so the
# subtraction yielded ~time.time() (~1.78e9 s) instead of a short duration —
# *1000 gave response_ms ~1.78e12, which overflowed the INTEGER
# agents.task_conformance_response_ms column and made every registration fail
# with "invalid input for query argument $3: ... (value out of int32 range)".
#
# These tests pin response_ms to the int32 range on both code paths. If the
# clock mismatch is reintroduced, response_ms blows past PG_INT32_MAX and they
# fail.


def _async_iter(items):
    """Wrap a list as an async iterator (mock for client.send_message)."""
    async def _gen():
        for item in items:
            yield item
    return _gen()


@patch("app.smoke_test.ClientFactory")
async def test_smoke_test_response_ms_fits_int32_on_success(mock_factory_cls):
    mock_client = MagicMock()
    mock_client.send_message = MagicMock(return_value=_async_iter([object()]))
    mock_factory = MagicMock()
    mock_factory.create_from_url = AsyncMock(return_value=mock_client)
    mock_factory_cls.return_value = mock_factory

    category, _note, response_ms = await smoke_test(
        "https://example.com/.well-known/agent.json"
    )

    assert category == "WORKING"
    assert response_ms is not None
    assert 0 <= response_ms <= PG_INT32_MAX, (
        f"response_ms={response_ms} does not fit a PostgreSQL INTEGER column — "
        "smoke_test() is mixing time.monotonic() and time.time()"
    )
    # A smoke test cannot legitimately run longer than its 15s timeout.
    assert response_ms < 60_000


@patch("app.smoke_test.ClientFactory")
async def test_smoke_test_response_ms_fits_int32_on_failure(mock_factory_cls):
    # The except branch computes response_ms too — it must also fit int32.
    mock_factory = MagicMock()
    mock_factory.create_from_url = AsyncMock(side_effect=RuntimeError("boom"))
    mock_factory_cls.return_value = mock_factory

    _category, _note, response_ms = await smoke_test(
        "https://example.com/.well-known/agent.json"
    )

    assert response_ms is not None
    assert 0 <= response_ms <= PG_INT32_MAX, (
        f"response_ms={response_ms} does not fit a PostgreSQL INTEGER column — "
        "smoke_test() is mixing time.monotonic() and time.time()"
    )
    assert response_ms < 60_000
