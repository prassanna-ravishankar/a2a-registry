"""
Send a real A2A `message/send` to an agent and classify the result.

Used at registration time to validate that the card actually leads to a working
A2A endpoint. Returns a category + maintainer-note-ready message.
"""

import uuid
from typing import Optional
from urllib.parse import urlparse

import httpx
import structlog
from a2a.client import ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, SendMessageRequest

logger = structlog.get_logger()

SMOKE_TEST_TIMEOUT_SECONDS = 15
SMOKE_TEST_MESSAGE = "Hello, what can you do?"


CATEGORY_NOTES = {
    "WORKING": "Verified working at registration. Agent responds to `message/send` correctly via the A2A SDK.",
    "NO_TRANSPORTS": "Agent card does not declare any transports compatible with the A2A SDK (e.g. JSONRPC). The SDK cannot connect even though the card validates.",
    "404": "Agent card is valid but the A2A endpoint returns **404 Not Found** when sending messages. The `message/send` endpoint does not exist at the URL declared in the agent card.",
    "405": "Agent card is valid but the A2A endpoint returns **405 Method Not Allowed**. Ensure your server accepts POST requests for `message/send` at the URL in your agent card.",
    "401": "Agent endpoint returns **401 Unauthorized**. Callers need credentials, but the agent card should declare `securitySchemes` and `security` so clients know how to authenticate. See the A2A spec.",
    "403": "Agent endpoint returns **403 Forbidden** when sending messages. Either the endpoint requires authentication that's not declared in the agent card, or callers are being blocked.",
    "402": "Agent endpoint returns **402 Payment Required**. Payment-gated agents should declare this in the agent card so clients know what credentials/payment to provide.",
    "400": "Agent endpoint returns **400 Bad Request** for a standard A2A `message/send` JSON-RPC payload. The request shape may not match what the server expects, or the server may require non-standard fields.",
    "DNS": "Agent card URL fails DNS resolution. The host appears to be down or decommissioned.",
    "VERSION": "Agent declares an unsupported A2A protocol version. The SDK expects '1.0' but received a different version string.",
    "BAD_RESPONSE": "Agent responds but the response shape is missing required A2A fields. Standard A2A SDK clients cannot parse the response. Update your response format to match the A2A spec.",
    "BAD_JSON": "Agent endpoint does not return valid JSON for `message/send` requests. Ensure the endpoint returns a proper JSON-RPC response.",
    "METHOD": "Agent does not implement the `message/send` JSON-RPC method. Add support for this method per the A2A spec.",
    "PARSE": "Agent's gRPC/protobuf response includes a field not defined in the A2A schema. Align response with the latest A2A spec.",
    "AUTH_BACKEND": "Agent endpoint reachable but returns an internal authentication error from a downstream LLM provider (invalid API key on the agent's side). The agent operator needs to fix their backend credentials.",
    "INTERNAL": "Agent endpoint reachable but returns an A2A `InternalError` when handling `message/send`. Check server-side error logs.",
    "TIMEOUT": "Agent endpoint did not respond within the smoke-test timeout. Could be transient; will be re-checked by the health worker.",
    "OTHER": "Smoke test against `message/send` failed with an unrecognised error. See full message in the registry's worker logs.",
}


def classify_error(exc: BaseException) -> str:
    """Map a smoke-test exception to a category string."""
    name = type(exc).__name__
    text = str(exc)

    if name == "VersionNotSupportedError":
        return "VERSION"
    if name == "ParseError" and "no field named" in text:
        return "PARSE"
    if name == "AgentCardResolutionError" and (
        "nodename nor servname" in text or "Network communication error" in text
    ):
        return "DNS"
    if "no compatible transports" in text:
        return "NO_TRANSPORTS"
    if name in ("ValidationError",) or "Response has neither task nor message" in text or "Either result or error should be used" in text:
        return "BAD_RESPONSE"
    if "JSON Decode Error" in text:
        return "BAD_JSON"
    if "MethodNotFoundError" in name or ("method" in text.lower() and "not found" in text.lower()):
        return "METHOD"
    if "InternalError" in name and "authentication_error" in text:
        return "AUTH_BACKEND"
    if "InternalError" in name:
        return "INTERNAL"
    for code in ("404", "405", "401", "402", "403", "400"):
        if f"HTTP Error: {code}" in text or f"HTTP Error {code}" in text:
            return code
    if "TimeoutError" in name or "ReadTimeout" in name:
        return "TIMEOUT"
    return "OTHER"


async def smoke_test(well_known_uri: str) -> tuple[str, str]:
    """
    Send a real A2A message/send to the agent and classify the result.

    Returns (category, maintainer_note). Category is one of the keys in
    CATEGORY_NOTES; maintainer_note is the human-readable message to store.
    """
    parsed = urlparse(well_known_uri)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    card_path = parsed.path or None

    try:
        async with httpx.AsyncClient(
            timeout=SMOKE_TEST_TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as http_client:
            factory = ClientFactory(
                ClientConfig(httpx_client=http_client, streaming=False),
            )
            client = await factory.create_from_url(base_url, relative_card_path=card_path)
            message = Message(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_USER,
                parts=[Part(text=SMOKE_TEST_MESSAGE)],
            )
            request = SendMessageRequest(message=message)
            saw_event = False
            async for _ in client.send_message(request):
                saw_event = True
            if not saw_event:
                return "BAD_RESPONSE", CATEGORY_NOTES["BAD_RESPONSE"]
            return "WORKING", CATEGORY_NOTES["WORKING"]
    except Exception as exc:
        category = classify_error(exc)
        logger.info(
            "smoke_test_failed",
            well_known_uri=well_known_uri,
            category=category,
            exc_type=type(exc).__name__,
            exc_msg=str(exc)[:200],
        )
        return category, CATEGORY_NOTES.get(category, CATEGORY_NOTES["OTHER"])


# Categories that should hard-reject registration (operator must fix the card).
HARD_REJECT_CATEGORIES: frozenset[str] = frozenset({"NO_TRANSPORTS", "VERSION"})


def should_reject(category: str) -> bool:
    return category in HARD_REJECT_CATEGORIES


def rejection_message(category: str) -> Optional[str]:
    if category not in HARD_REJECT_CATEGORIES:
        return None
    return CATEGORY_NOTES.get(category)
