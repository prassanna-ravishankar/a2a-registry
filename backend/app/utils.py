"""Utility functions for agent validation and tracking"""

import asyncio
import ipaddress
import logging
import socket
from typing import Any, Optional, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
from aiohttp.abc import AbstractResolver

from .config import settings
from .models import AgentCreate
from .validators import _normalise_fields, validate_agent_card

logger = logging.getLogger(__name__)

try:
    from posthog import Posthog

    posthog_client = (
        Posthog(settings.posthog_api_key, host=settings.posthog_host)
        if settings.posthog_enabled and settings.posthog_api_key
        else None
    )
except Exception:
    posthog_client = None


_BLOCKED_HOSTS = frozenset({
    "localhost",
    "metadata.google.internal",
    "metadata.google",
    "kubernetes.default.svc",
})

_BLOCKED_SUFFIXES = (".internal", ".local", ".svc", ".cluster.local")
_CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")
_MAX_AGENT_CARD_REDIRECTS = 3


def _is_private_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    if ip.version == 4 and ip in _CGNAT_NETWORK:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _is_blocked_hostname(hostname: str) -> bool:
    host = hostname.rstrip(".").lower()
    return host in _BLOCKED_HOSTS or any(host.endswith(suffix) for suffix in _BLOCKED_SUFFIXES)


class _PinnedResolver(AbstractResolver):
    """aiohttp resolver that reuses the addresses already passed by the SSRF guard."""

    def __init__(self, hostname: str, records: list[dict[str, Any]]):
        self.hostname = hostname.rstrip(".").lower()
        self.records = records

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_INET,
    ) -> list[dict[str, Any]]:
        if host.rstrip(".").lower() != self.hostname:
            raise OSError(f"Unexpected host during guarded fetch: {host}")
        if family not in (socket.AF_UNSPEC, 0):
            filtered = [record for record in self.records if record["family"] == family]
            if filtered:
                return filtered
        return self.records

    async def close(self) -> None:
        pass


async def _resolve_public_addresses(hostname: str, port: int) -> list[dict[str, Any]]:
    if _is_blocked_hostname(hostname):
        raise ValueError(f"Host '{hostname}' is not publicly reachable")

    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(
            hostname,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve host '{hostname}'") from exc

    records: list[dict[str, Any]] = []
    seen: set[tuple[int, str, int]] = set()
    for family, _, proto, _, address in infos:
        if family == socket.AF_INET6:
            resolved_host, resolved_port = address[:2]
        elif family == socket.AF_INET:
            resolved_host, resolved_port = address
        else:
            continue

        if _is_private_address(resolved_host):
            raise ValueError(f"Host '{hostname}' resolves to a non-public address")

        key = (family, resolved_host, resolved_port)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            {
                "hostname": hostname,
                "host": resolved_host,
                "port": resolved_port,
                "family": family,
                "proto": proto,
                "flags": socket.AI_NUMERICHOST,
            }
        )

    if not records:
        raise ValueError(f"Could not resolve host '{hostname}'")
    return records


async def _guarded_connector_for_url(url: str) -> aiohttp.TCPConnector:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Agent card URL must use http or https")
    if not parsed.hostname:
        raise ValueError("Agent card URL must include a hostname")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    records = await _resolve_public_addresses(parsed.hostname, port)
    return aiohttp.TCPConnector(
        resolver=_PinnedResolver(parsed.hostname, records),
        family=socket.AF_UNSPEC,
    )


def _redirect_url(current_url: str, location: str | None) -> str:
    if not location:
        raise ValueError("Redirect response missing Location header")
    next_url = urljoin(current_url, location)
    parsed = urlparse(next_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Redirect target must use http or https")
    return next_url


async def _get_guarded_json(url: str, *, user_agent: str) -> Tuple[Optional[dict[str, Any]], Optional[str]]:
    current_url = url
    for _redirect_count in range(_MAX_AGENT_CARD_REDIRECTS + 1):
        connector = await _guarded_connector_for_url(current_url)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                current_url,
                timeout=aiohttp.ClientTimeout(total=settings.health_check_timeout_seconds),
                headers={
                    "User-Agent": user_agent,
                    "Accept": "application/json",
                },
                allow_redirects=False,
            ) as response:
                if 300 <= response.status < 400:
                    current_url = _redirect_url(current_url, response.headers.get("Location"))
                    continue
                if response.status != 200:
                    return None, f"Agent card endpoint returned HTTP {response.status}"

                try:
                    return await response.json(), None
                except Exception as e:
                    return None, f"Invalid JSON in agent card: {e}"

    return None, "Too many redirects while fetching agent card"


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
        remote_agent, error = await _get_guarded_json(
            well_known_uri,
            user_agent="A2A-Registry-Backend/1.0",
        )
        if error:
            return False, error
        if remote_agent is None:
            return False, "Internal error: well-known fetch returned no data"

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
                "Field mismatches found:\n  " + "\n  ".join(mismatches),
            )

        return True, "Ownership verified successfully"

    except ValueError as e:
        return False, str(e)
    except aiohttp.ClientError as e:
        return False, f"Network error accessing {well_known_uri}: {e}"
    except Exception:
        logger.exception("well_known_fetch_unexpected_error", extra={"uri": well_known_uri})
        return False, "Unexpected error while fetching the well-known URI"


async def fetch_agent_card(well_known_uri: str) -> Tuple[Optional[dict[str, Any]], Optional[str]]:
    """
    Fetch an agent card from a wellKnownURI.

    Args:
        well_known_uri: The URL to fetch the agent card from

    Returns:
        Tuple of (agent_card_dict or None, error_message or None)
    """
    try:
        agent_card, error = await _get_guarded_json(
            well_known_uri,
            user_agent="A2A-Registry/1.0",
        )
        if error:
            return None, error
        if agent_card is None:
            return None, "Internal error: agent card fetch returned no data"

        normalised = _normalise_fields(agent_card)
        validation_errors = validate_agent_card(normalised)
        if validation_errors:
            return None, "Agent card validation failed: " + "; ".join(validation_errors)

        return normalised, None

    except ValueError as e:
        return None, str(e)
    except aiohttp.ClientError as e:
        return None, f"Network error fetching agent card: {e}"
    except Exception:
        logger.exception("agent_card_fetch_unexpected_error")
        return None, "Unexpected error while fetching the agent card"


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
