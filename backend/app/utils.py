"""Utility functions for agent validation and tracking"""

import aiohttp
from typing import Any, Optional, Tuple

from .config import settings
from .models import AgentCreate
from .validators import _SDK_AVAILABLE, _normalise_fields, validate_agent_card, validate_well_known_uri

if _SDK_AVAILABLE:
    from a2a.types import AgentCard as _AgentCard
    from pydantic import ValidationError as _ValidationError

try:
    from posthog import Posthog

    posthog_client = (
        Posthog(settings.posthog_api_key, host=settings.posthog_host)
        if settings.posthog_enabled and settings.posthog_api_key
        else None
    )
except Exception:
    posthog_client = None


async def verify_well_known_uri(agent_data: AgentCreate) -> Tuple[bool, str]:
    """
    Verify agent ownership by fetching wellKnownURI and comparing key fields.

    Args:
        agent_data: Agent data to verify

    Returns:
        Tuple of (verified: bool, message: str)
    """
    well_known_uri = str(agent_data.wellKnownURI)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                well_known_uri,
                timeout=aiohttp.ClientTimeout(total=settings.health_check_timeout_seconds),
                headers={
                    "User-Agent": "A2A-Registry-Backend/1.0",
                    "Accept": "application/json",
                },
            ) as response:
                if response.status != 200:
                    return (
                        False,
                        f"Well-known endpoint returned HTTP {response.status}",
                    )

                try:
                    remote_agent = await response.json()
                except Exception as e:
                    return False, f"Invalid JSON in well-known endpoint: {e}"

                # Compare key fields
                mismatches = []
                for field in ["name", "description"]:
                    local_val = getattr(agent_data, field)
                    remote_val = remote_agent.get(field)
                    if local_val != remote_val:
                        mismatches.append(
                            f"{field}: local='{local_val}' vs remote='{remote_val}'"
                        )

                if mismatches:
                    return (
                        False,
                        f"Field mismatches found:\n  " + "\n  ".join(mismatches),
                    )

                return True, "Ownership verified successfully"

    except aiohttp.ClientError as e:
        return False, f"Network error accessing {well_known_uri}: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


async def fetch_agent_card(well_known_uri: str) -> Tuple[Optional[dict[str, Any]], Optional[str]]:
    """
    Fetch an agent card from a wellKnownURI.

    Args:
        well_known_uri: The URL to fetch the agent card from

    Returns:
        Tuple of (agent_card_dict or None, error_message or None)
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                well_known_uri,
                timeout=aiohttp.ClientTimeout(total=settings.health_check_timeout_seconds),
                headers={
                    "User-Agent": "A2A-Registry/1.0",
                    "Accept": "application/json",
                },
            ) as response:
                if response.status != 200:
                    return None, f"Agent card endpoint returned HTTP {response.status}"

                try:
                    agent_card = await response.json()
                except Exception as e:
                    return None, f"Invalid JSON in agent card: {e}"

                # Validate agent card structure; when SDK is available, parse
                # through AgentCard so the returned dict uses canonical field
                # names and includes SDK-computed defaults.
                normalised = _normalise_fields(agent_card)
                if _SDK_AVAILABLE:
                    try:
                        parsed = _AgentCard.model_validate(normalised)
                        return parsed.model_dump(mode="json", by_alias=True), None
                    except _ValidationError as exc:
                        errors = [f"{' -> '.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
                        return None, "Agent card validation failed: " + "; ".join(errors)

                # SDK not available - fall back to manual validation
                validation_errors = validate_agent_card(normalised)
                if validation_errors:
                    return None, "Agent card validation failed: " + "; ".join(validation_errors)

                return normalised, None

    except aiohttp.ClientError as e:
        return None, f"Network error fetching agent card: {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"


def track_event(event_name: str, properties: dict | None = None):
    """Track an event to PostHog"""
    if posthog_client and settings.posthog_enabled:
        try:
            posthog_client.capture("api_user", event_name, properties or {})
        except Exception:
            # Silently fail - analytics shouldn't break the app
            pass


def track_api_query(endpoint: str, **kwargs):
    """Track an API query"""
    track_event(
        "api_query",
        {
            "endpoint": endpoint,
            **kwargs,
        },
    )
