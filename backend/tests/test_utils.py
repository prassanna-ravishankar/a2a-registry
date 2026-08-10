"""Tests for utility functions that perform outbound network fetches."""

import json
import socket
from unittest.mock import patch

import pytest

from app import utils

from .conftest import MOCK_AGENT_CARD


async def test_fetch_agent_card_rejects_loopback_before_http():
    """Direct private IPs must be rejected before creating an HTTP session."""
    with patch("app.utils.aiohttp.ClientSession", side_effect=AssertionError("no HTTP")):
        card, error = await utils.fetch_agent_card("http://127.0.0.1/.well-known/agent.json")

    assert card is None
    assert "non-public" in error


async def test_fetch_agent_card_rejects_if_any_resolved_address_is_private(monkeypatch):
    """A hostname is unsafe if any DNS answer is private, not just the first."""
    calls = []

    async def fake_getaddrinfo(host, port, family=0, type=0):
        calls.append((host, port, family, type))
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", port)),
        ]

    loop = utils.asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)

    with patch("app.utils.aiohttp.ClientSession", side_effect=AssertionError("no HTTP")):
        card, error = await utils.fetch_agent_card(
            "https://mixed.example/.well-known/agent.json"
        )

    assert card is None
    assert "non-public" in error
    assert calls


@pytest.mark.parametrize(
    "url",
    [
        "http://[::1]/.well-known/agent.json",
        "http://[::ffff:127.0.0.1]/.well-known/agent.json",
        "http://169.254.169.254/latest/meta-data",
        "http://100.64.0.1/.well-known/agent.json",
        "http://metadata.google.internal/.well-known/agent.json",
        "http://kubernetes.default.svc/.well-known/agent.json",
    ],
)
async def test_fetch_agent_card_rejects_internal_url_forms(url):
    with patch("app.utils.aiohttp.ClientSession", side_effect=AssertionError("no HTTP")):
        card, error = await utils.fetch_agent_card(url)

    assert card is None
    assert error


async def test_fetch_agent_card_follows_public_redirect_with_each_hop_guarded(monkeypatch):
    """Public canonical redirects are allowed, but aiohttp auto-follow stays disabled."""
    connector = object()
    guarded_urls = []
    get_calls = []

    async def fake_guarded_connector(url):
        guarded_urls.append(url)
        return connector

    class FakeResponse:
        def __init__(self, status, headers=None, payload=None):
            self.status = status
            self.headers = headers or {}
            self.payload = payload or MOCK_AGENT_CARD
            self.content_length = None
            self.content = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def iter_chunked(self, _chunk_size):
            yield json.dumps(self.payload).encode()

    class FakeSession:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url, **kwargs):
            get_calls.append((url, kwargs))
            if len(get_calls) == 1:
                return FakeResponse(301, headers={"Location": "/.well-known/agent-card.json"})
            return FakeResponse(200)

    monkeypatch.setattr(utils, "_guarded_connector_for_url", fake_guarded_connector)
    monkeypatch.setattr(utils.aiohttp, "ClientSession", FakeSession)

    card, error = await utils.fetch_agent_card("https://example.com/.well-known/agent.json")

    assert error is None
    assert card["name"] == MOCK_AGENT_CARD["name"]
    assert guarded_urls == [
        "https://example.com/.well-known/agent.json",
        "https://example.com/.well-known/agent-card.json",
    ]
    assert [call[0] for call in get_calls] == guarded_urls
    assert all(call[1]["allow_redirects"] is False for call in get_calls)


async def test_fetch_agent_card_rejects_private_redirect_target(monkeypatch):
    """A redirect hop is rejected if its target fails the same SSRF guard."""
    guarded_urls = []

    async def fake_guarded_connector(url):
        guarded_urls.append(url)
        if url.startswith("http://127.0.0.1"):
            raise ValueError("Host '127.0.0.1' resolves to a non-public address")
        return object()

    class FakeResponse:
        status = 302
        headers = {"Location": "http://127.0.0.1/.well-known/agent.json"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(utils, "_guarded_connector_for_url", fake_guarded_connector)
    monkeypatch.setattr(utils.aiohttp, "ClientSession", FakeSession)

    card, error = await utils.fetch_agent_card("https://example.com/.well-known/agent.json")

    assert card is None
    assert "non-public" in error
    assert guarded_urls == [
        "https://example.com/.well-known/agent.json",
        "http://127.0.0.1/.well-known/agent.json",
    ]


async def test_fetch_agent_card_accepts_public_non_redirect(monkeypatch):
    connector = object()

    async def fake_guarded_connector(_url):
        return connector

    class FakeResponse:
        status = 200
        content_length = None
        content = None

        def __init__(self):
            self.content = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def iter_chunked(self, _chunk_size):
            yield json.dumps(MOCK_AGENT_CARD).encode()

    class FakeSession:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(utils, "_guarded_connector_for_url", fake_guarded_connector)
    monkeypatch.setattr(utils.aiohttp, "ClientSession", FakeSession)

    card, error = await utils.fetch_agent_card("https://example.com/.well-known/agent.json")

    assert error is None
    assert card["name"] == MOCK_AGENT_CARD["name"]


async def test_fetch_agent_card_rejects_oversized_content_length(monkeypatch):
    async def fake_guarded_connector(_url):
        return object()

    class FakeResponse:
        status = 200
        content_length = utils._MAX_AGENT_CARD_BYTES + 1

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(utils, "_guarded_connector_for_url", fake_guarded_connector)
    monkeypatch.setattr(utils.aiohttp, "ClientSession", FakeSession)

    card, error = await utils.fetch_agent_card("https://example.com/.well-known/agent.json")

    assert card is None
    assert "byte limit" in error


async def test_fetch_agent_card_reads_chunked_body_to_eof(monkeypatch):
    """A stream read may produce partial chunks before the complete JSON body."""
    payload = json.dumps(MOCK_AGENT_CARD).encode()
    split_at = len(payload) // 2

    async def fake_guarded_connector(_url):
        return object()

    class FakeResponse:
        status = 200
        content_length = len(payload)
        content = None

        def __init__(self):
            self.content = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def iter_chunked(self, _chunk_size):
            yield payload[:split_at]
            yield payload[split_at:]

    class FakeSession:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(utils, "_guarded_connector_for_url", fake_guarded_connector)
    monkeypatch.setattr(utils.aiohttp, "ClientSession", FakeSession)

    card, error = await utils.fetch_agent_card(
        "https://example.com/.well-known/agent.json"
    )

    assert error is None
    assert card["name"] == MOCK_AGENT_CARD["name"]


async def test_bounded_body_rejects_chunked_payload_over_limit():
    class FakeContent:
        async def iter_chunked(self, _chunk_size):
            yield b"1234"
            yield b"5678"

    assert await utils._read_bounded_body(FakeContent(), 7) is None
