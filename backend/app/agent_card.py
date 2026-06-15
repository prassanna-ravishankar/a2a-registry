"""Helpers for turning a fetched agent card (dict) into an AgentCreate.

Shared by the registration/PUT routes (app.main) and the background worker
(worker.py) so both build the stored agent record from a live card exactly the
same way. Supports both A2A v0.3 (top-level url/protocolVersion) and v1.0
(interfaces[].url / supportedInterfaces[].url) card formats.
"""

from typing import Any, Optional

from .models import AgentCreate


def extract_agent_url(card: dict[str, Any]) -> str:
    """Extract the primary agent URL from a card, supporting v0.3 and v1.0.

    v0.3: top-level ``url`` field.
    v1.0: ``interfaces[0].url`` (or ``supportedInterfaces[0].url``).
    """
    if "url" in card:
        return card["url"]
    for key in ("interfaces", "supportedInterfaces"):
        interfaces = card.get(key)
        if isinstance(interfaces, list) and interfaces:
            url = interfaces[0].get("url")
            if url:
                return url
    raise KeyError("Agent card has no 'url' field and no 'interfaces[].url' — cannot determine endpoint")


def extract_protocol_version(card: dict[str, Any]) -> str:
    """Extract protocol version, supporting both v0.3 and v1.0 formats."""
    if "protocolVersion" in card:
        return card["protocolVersion"]
    for key in ("interfaces", "supportedInterfaces"):
        interfaces = card.get(key)
        if isinstance(interfaces, list) and interfaces:
            pv = interfaces[0].get("protocolVersion")
            if pv:
                return pv
    return "unknown"


def agent_create_from_card(
    agent_card: dict[str, Any],
    well_known_uri: str,
    *,
    author_override: Optional[str] = None,
    author_fallback: str = "Unknown",
) -> AgentCreate:
    """Build an AgentCreate from a fetched agent card dict.

    Supports both v0.3 and v1.0 A2A Protocol agent card formats.

    Raises ValueError if the card is missing required fields or is otherwise
    malformed. Callers in HTTP context map this to a 400; the worker logs and
    skips. (Keeping this transport-agnostic is why it raises ValueError rather
    than HTTPException.)
    """
    try:
        # v1.0 moves supportsAuthenticatedExtendedCard into capabilities.extendedAgentCard
        capabilities = agent_card.get(
            "capabilities",
            {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
        )

        return AgentCreate(
            protocolVersion=extract_protocol_version(agent_card),
            name=agent_card["name"],
            description=agent_card.get("description", ""),
            author=author_override or (agent_card.get("provider") or {}).get("organization", author_fallback),
            wellKnownURI=well_known_uri,
            url=extract_agent_url(agent_card),
            version=agent_card.get("version", "1.0.0"),
            provider=agent_card.get("provider"),
            documentationUrl=agent_card.get("documentationUrl"),
            capabilities=capabilities,
            defaultInputModes=agent_card.get("defaultInputModes", ["text/plain"]),
            defaultOutputModes=agent_card.get("defaultOutputModes", ["text/plain"]),
            skills=agent_card.get("skills", []),
        )
    except KeyError as e:
        raise ValueError(f"Invalid agent card: missing {e}")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Invalid agent card format: {e}")
