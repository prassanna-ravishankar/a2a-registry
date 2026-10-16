"""Per-client request limits and the service-wide Jev spend ceiling.

Counters live in Postgres, so every limit holds across API replicas, the
worker and restarts. Each limit is a fixed window; a request that would take
any counter past its limit is refused with the seconds until that window ends.
"""

import ipaddress
import math
import time
from dataclasses import dataclass, replace
from typing import Optional, Sequence

from fastapi import Request

from .config import settings

# Source of every request that reaches the API through the GKE gateway. Only
# from these peers is X-Forwarded-For trusted, and only the hop Google appended.
# https://cloud.google.com/load-balancing/docs/https#source_ip_addresses
GOOGLE_FRONTENDS = tuple(ipaddress.ip_network(n) for n in ("35.191.0.0/16", "130.211.0.0/22"))

# https://www.cloudflare.com/ips/ (October 2026). A request whose gateway hop is
# one of these came through Cloudflare, which overwrites CF-Connecting-IP.
CLOUDFLARE = tuple(ipaddress.ip_network(n) for n in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "141.101.64.0/18",
    "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17",
    "162.158.0.0/15", "104.16.0.0/13", "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32", "2405:8100::/32",
    "2a06:98c0::/29", "2c0f:f248::/32",
))


@dataclass(frozen=True)
class Limit:
    name: str
    count: int
    seconds: int
    message: str

    def of(self, key: str) -> "Limit":
        return replace(self, name=f"{self.name}:{key}")


class RateLimitError(Exception):
    """A limit tripped. The API answers 429 with Retry-After."""

    def __init__(self, limit: Limit, retry_after: int):
        super().__init__(limit.name)
        self.limit = limit
        self.retry_after = retry_after


class BudgetUnavailableError(Exception):
    """The Jev budget could not be checked, so nothing may be sent. The API answers 503."""


# Outcomes of a Jev reservation that must stop a classification without any
# write: neither a classifier failure nor a reason to store "unscored".
NOT_SENT = (RateLimitError, BudgetUnavailableError)


_CLIENT = "Too many requests from this address. Retry after the time in the Retry-After header."
_CAPACITY = (
    "The registry has reached its review capacity for now, so it is not accepting submissions."
    " Retry after the time in the Retry-After header."
)

HOUR, DAY = 3600, 86400

# Per client. Both registration endpoints share SUBMIT.
SUBMIT = (Limit("submit", 10, HOUR, _CLIENT), Limit("submit-day", 30, DAY, _CLIENT))
PREVIEW = (Limit("preview", 30, HOUR, _CLIENT),)
RECHECK = (Limit("recheck", 5, HOUR, _CLIENT),)
RECHECK_AGENT = Limit("recheck-agent", 4, HOUR, "This agent was rechecked recently. Retry after the time in the Retry-After header.")
FLAG = (Limit("flag", 5, HOUR, _CLIENT),)
CHAT = (Limit("chat", 30, 60, _CLIENT),)


def jev_limits(client: Optional[str]) -> tuple[Limit, ...]:
    """Jev requests one classification may draw on, counted per request (card window).

    Every Jev request counts against the daily ceiling. Public submissions also
    draw on a per-client allowance and on a share of the ceiling of their own, so
    a flood cannot use the worker's headroom for changed cards.
    """
    ceiling = Limit("jev", settings.jev_daily_requests, DAY, _CAPACITY)
    if client is None:
        return (ceiling,)
    return (
        Limit("jev-client", settings.jev_client_daily_requests, DAY, _CLIENT).of(client),
        Limit("jev-submissions-hour", settings.jev_submission_hourly_requests, HOUR, _CAPACITY),
        Limit("jev-submissions", settings.jev_submission_daily_requests, DAY, _CAPACITY),
        ceiling,
    )


def _ip(value: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _within(ip, networks) -> bool:
    return ip is not None and any(ip in network for network in networks)


def client_key(request: Request) -> str:
    """The address a limit is keyed on, which a client cannot choose.

    Behind the gateway the last X-Forwarded-For entry is Google's and the one
    before it is the peer Google saw. That peer is Cloudflare for proxied traffic,
    whose CF-Connecting-IP is then the client; otherwise it is the client, who
    reached the gateway directly. Everything earlier in the header is the
    client's to forge and is ignored. IPv6 clients are keyed by /64.
    """
    peer = request.client.host if request.client else ""
    ip = _ip(peer)
    if _within(ip, GOOGLE_FRONTENDS):
        hops = request.headers.get("x-forwarded-for", "").split(",")
        edge = _ip(hops[-2]) if len(hops) >= 2 else None
        if _within(edge, CLOUDFLARE):
            ip = _ip(request.headers.get("cf-connecting-ip", "")) or edge
        elif edge is not None:
            ip = edge
    if ip is None:
        return peer or "unknown"
    if ip.version == 6:
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


TAKE_SQL = """
    INSERT INTO rate_limit_counters (scope, window_end, used) VALUES ($1, $2, $3)
    ON CONFLICT (scope, window_end) DO UPDATE SET used = rate_limit_counters.used + EXCLUDED.used
        WHERE rate_limit_counters.used + EXCLUDED.used <= $4
    RETURNING used
"""
GIVE_BACK_SQL = "UPDATE rate_limit_counters SET used = used - $3 WHERE scope = $1 AND window_end = $2"
USED_SQL = "SELECT used FROM rate_limit_counters WHERE scope = $1 AND window_end = $2"
PRUNE_SQL = "DELETE FROM rate_limit_counters WHERE window_end <= $1"


def _window_end(limit: Limit, now: float) -> int:
    return (int(now) // limit.seconds + 1) * limit.seconds


def _refusal(limit: Limit, now: float) -> RateLimitError:
    return RateLimitError(limit, max(1, math.ceil(_window_end(limit, now) - now)))


async def take(db, limits: Sequence[Limit], cost: int = 1) -> None:
    """Count `cost` against every limit, or against none and raise RateLimitError."""
    now = time.time()
    taken: list[Limit] = []
    for limit in limits:
        used = None
        if cost <= limit.count:
            used = await db.fetchval(TAKE_SQL, limit.name, _window_end(limit, now), cost, limit.count)
        if used is None:
            for done in taken:
                await db.execute(GIVE_BACK_SQL, done.name, _window_end(done, now), cost)
            raise _refusal(limit, now)
        taken.append(limit)


async def ensure_available(db, limits: Sequence[Limit]) -> None:
    """Raise RateLimitError if any limit is already used up, without counting."""
    now = time.time()
    for limit in limits:
        used = await db.fetchval(USED_SQL, limit.name, _window_end(limit, now)) or 0
        if used >= limit.count:
            raise _refusal(limit, now)


async def limit_client(db, request: Request, limits: Sequence[Limit]) -> None:
    if settings.rate_limit_enabled:
        await take(db, [limit.of(client_key(request)) for limit in limits])


async def prune(db) -> None:
    await db.execute(PRUNE_SQL, int(time.time()))


class JevBudget:
    """Meters Jev requests for one caller: the worker or admin (client None), or a public submitter."""

    def __init__(self, db, client: Optional[str] = None):
        self.db = db
        self.limits = jev_limits(client)

    async def ensure_available(self) -> None:
        await ensure_available(self.db, self.limits)

    async def reserve(self, requests: int) -> None:
        try:
            await take(self.db, self.limits, requests)
        except RateLimitError:
            raise
        except Exception as exc:
            raise BudgetUnavailableError(type(exc).__name__) from exc
