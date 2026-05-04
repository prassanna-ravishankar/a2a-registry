"""Tests for the registration-time smoke-test classifier."""

from app.smoke_test import (
    CATEGORY_NOTES,
    HARD_REJECT_CATEGORIES,
    classify_error,
    rejection_message,
    should_reject,
)


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
