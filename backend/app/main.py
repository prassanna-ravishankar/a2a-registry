"""FastAPI application - main entry point"""

import ipaddress
import time
import uuid
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Any, Optional
from urllib.parse import urlparse
from uuid import UUID

import httpx
import structlog
from a2a.client import ClientConfig, ClientFactory
from a2a.client.card_resolver import parse_agent_card
from a2a.types import Message, Part, Role, SendMessageRequest, Task, TaskState
from fastapi import APIRouter, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .agent_card import agent_create_from_card
from .config import settings
from .database import db
from .mcp_server import mcp
from .models import (
    AgentCreate,
    AgentFlag,
    AgentPublic,
    AgentRegister,
    HealthStatus,
    PaginatedAgents,
    RegistryStats,
    UptimeMetrics,
)
from .repositories import AgentRepository, FlagRepository, HealthCheckRepository, StatsRepository
from .smoke_test import rejection_message, should_reject, smoke_test
from .utils import fetch_agent_card, track_api_query, verify_well_known_uri
from .validators import validate_well_known_uri

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)


def _agent_create_from_card(
    agent_card: dict[str, Any],
    well_known_uri: str,
    *,
    author_override: Optional[str] = None,
    author_fallback: str = "Unknown",
) -> AgentCreate:
    """HTTP wrapper around agent_card.agent_create_from_card.

    Maps the transport-agnostic ValueError to a 400 so registration/PUT keep
    their existing API contract. The actual card-parsing logic is shared with
    the worker (see app.agent_card).
    """
    try:
        return agent_create_from_card(
            agent_card,
            well_known_uri,
            author_override=author_override,
            author_fallback=author_fallback,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _make_mcp_app():
    return mcp.http_app(path="/", stateless_http=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    _mcp = _make_mcp_app()
    app.mount("/mcp", _mcp)
    async with _mcp.lifespan(app):
        await db.connect()
        print("✅ Database connected")
        yield
        await db.disconnect()
        print("👋 Database disconnected")


app = FastAPI(
    title="A2A Registry API",
    description="Community-driven directory of AI agents using the A2A Protocol",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create router for all API endpoints
logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def root():
    """API root - basic info"""
    return {
        "name": "A2A Registry API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "agents": "/agents",
            "stats": "/stats",
        },
    }


@router.get("/health")
async def health_check():
    """Health check endpoint for k8s"""
    return {"status": "healthy"}


# ============================================================================
# Agent Endpoints
# ============================================================================


@router.post("/agents/register", response_model=AgentPublic, status_code=201)
@limiter.limit("10/hour")
async def register_agent_simple(registration: AgentRegister, request: Request):
    """
    Register an agent by its wellKnownURI.

    Just provide the wellKnownURI and we'll fetch the agent card automatically.
    The agent card must be accessible and contain valid A2A Protocol fields.
    """
    well_known_uri = str(registration.wellKnownURI)
    track_api_query("POST /agents/register", wellKnownURI=well_known_uri)

    # Validate wellKnownURI format
    uri_errors = validate_well_known_uri(well_known_uri)
    if uri_errors:
        raise HTTPException(status_code=400, detail="; ".join(uri_errors))

    # Check if already exists (exact URI match)
    agent_repo = AgentRepository(db)
    existing = await agent_repo.get_by_well_known_uri(well_known_uri)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Agent already registered (id={existing.id}). Use PUT /agents/{existing.id} to update.",
        )

    # Check for duplicate by hostname (catches agent.json vs agent-card.json on same host)
    hostname = urlparse(well_known_uri).hostname or ""
    if hostname:
        host_duplicate = await agent_repo.get_by_host(hostname)
        if host_duplicate:
            raise HTTPException(
                status_code=409,
                detail=f"An agent from this host is already registered: '{host_duplicate.name}' (id={host_duplicate.id}). Use PUT /agents/{host_duplicate.id} to update it instead.",
            )

    # Fetch the agent card from the wellKnownURI
    agent_card, error = await fetch_agent_card(well_known_uri)
    if error:
        raise HTTPException(status_code=400, detail=f"Failed to fetch agent card: {error}")
    if agent_card is None:
        raise HTTPException(status_code=500, detail="Internal error: agent card fetch returned no data")

    agent_data = _agent_create_from_card(
        agent_card, well_known_uri, author_override=registration.author,
    )

    # Card-content dedup: catches the same card being re-registered under different
    # hostnames (e.g. one card served from many parked domains).
    card_duplicate = await agent_repo.get_by_name_and_author(agent_data.name, agent_data.author)
    if card_duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"An agent with name '{agent_data.name}' by '{agent_data.author}' is already registered (id={card_duplicate.id}). Use PUT /agents/{card_duplicate.id} to update it.",
        )

    # Smoke test: send a real `message/send` to confirm the card actually leads
    # to a working endpoint. Hard-reject categories that indicate a broken card.
    smoke_category, smoke_note, smoke_ms = await smoke_test(well_known_uri)
    if should_reject(smoke_category):
        raise HTTPException(status_code=400, detail=rejection_message(smoke_category) or "Agent failed smoke test")

    # Create agent, then attach smoke-test result as initial maintainer note
    # AND as the first task_conformance datapoint.
    try:
        created_agent = await agent_repo.create(agent_data)
        await agent_repo.update_maintainer_notes(created_agent.id, smoke_note)
        await agent_repo.update_task_conformance(created_agent.id, smoke_category, smoke_ms)
        result = await agent_repo.get_by_id(created_agent.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {e}")


@router.post("/agents", response_model=AgentPublic, status_code=201)
@limiter.limit("10/hour")
async def register_agent_full(agent: AgentCreate, request: Request):
    """
    Register a new agent with full payload.

    Validates ownership by fetching wellKnownURI and comparing key fields.
    For a simpler flow, use POST /agents/register with just the wellKnownURI.
    """
    track_api_query("POST /agents", author=agent.author)

    # Check if already exists (exact URI match)
    well_known_uri = str(agent.wellKnownURI)
    agent_repo = AgentRepository(db)
    existing = await agent_repo.get_by_well_known_uri(well_known_uri)
    if existing:
        logger.info("agent_duplicate", well_known_uri=well_known_uri)
        raise HTTPException(
            status_code=409,
            detail=f"Agent already registered (id={existing.id}). Use PUT /agents/{existing.id} to update.",
        )

    # Check for duplicate by hostname
    hostname = urlparse(well_known_uri).hostname or ""
    if hostname:
        host_duplicate = await agent_repo.get_by_host(hostname)
        if host_duplicate:
            raise HTTPException(
                status_code=409,
                detail=f"An agent from this host is already registered: '{host_duplicate.name}' (id={host_duplicate.id}). Use PUT /agents/{host_duplicate.id} to update it instead.",
            )

    # Card-content dedup: catches the same card being re-registered under different
    # hostnames (e.g. one card served from many parked domains).
    card_duplicate = await agent_repo.get_by_name_and_author(agent.name, agent.author)
    if card_duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"An agent with name '{agent.name}' by '{agent.author}' is already registered (id={card_duplicate.id}). Use PUT /agents/{card_duplicate.id} to update it.",
        )

    # Verify ownership via wellKnownURI
    verified, message = await verify_well_known_uri(agent)
    if not verified:
        raise HTTPException(status_code=400, detail=f"Ownership verification failed: {message}")

    # Smoke test the live endpoint and hard-reject obviously broken cards.
    smoke_category, smoke_note, smoke_ms = await smoke_test(well_known_uri)
    if should_reject(smoke_category):
        raise HTTPException(status_code=400, detail=rejection_message(smoke_category) or "Agent failed smoke test")

    # Create agent, then attach smoke-test result as initial maintainer note
    # AND as the first task_conformance datapoint.
    try:
        created_agent = await agent_repo.create(agent)
        await agent_repo.update_maintainer_notes(created_agent.id, smoke_note)
        await agent_repo.update_task_conformance(created_agent.id, smoke_category, smoke_ms)
        result = await agent_repo.get_by_id(created_agent.id)
        logger.info("agent_registered", well_known_uri=well_known_uri, smoke=smoke_category)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {e}")


@router.get("/agents", response_model=PaginatedAgents)
async def list_agents(
    skill: Optional[str] = None,
    capability: Optional[str] = None,
    author: Optional[str] = None,
    search: Optional[str] = None,
    conformance: Optional[str] = None,
    healthy: Optional[bool] = None,
    task_verified: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List agents with optional filtering and pagination.

    Query parameters:
    - search: Full-text search across name, description, and author
    - skill: Filter by skill ID
    - capability: Filter by A2A capability (e.g., "streaming")
    - author: Filter by author name (case-insensitive partial match)
    - conformance: Filter by conformance ("standard" or "non-standard")
    - healthy: Filter by health status (true = healthy, false = unhealthy)
    - task_verified: true = only agents whose last A2A message/send probe passed
    - limit: Max results to return (default: 50, max: 100)
    - offset: Pagination offset (default: 0)
    """
    track_api_query(
        "GET /agents",
        skill=skill,
        capability=capability,
        author=author,
        search=search,
        conformance=conformance,
        healthy=healthy,
        task_verified=task_verified,
        limit=limit,
        offset=offset,
    )

    # Validate limit
    if limit > 100:
        limit = 100

    # Validate conformance param
    if conformance not in (None, "standard", "non-standard"):
        conformance = None

    agent_repo = AgentRepository(db)
    agents, total = await agent_repo.list_agents(
        skill=skill,
        capability=capability,
        author=author,
        search=search,
        conformance=conformance,
        healthy=healthy,
        task_verified=task_verified,
        limit=limit,
        offset=offset,
    )

    return PaginatedAgents(
        agents=agents,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/agents/{agent_id}", response_model=AgentPublic)
async def get_agent(agent_id: UUID):
    """Get a single agent by ID with health metrics"""
    track_api_query("GET /agents/{id}", agent_id=str(agent_id))

    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent


@router.put("/agents/{agent_id}", response_model=AgentPublic)
async def update_agent(
    agent_id: UUID,
    request: Request,
    x_admin_key: Optional[str] = Header(default=None),
):
    """
    Re-fetch and update an agent's metadata from its wellKnownURI.

    By default re-fetches the agent's current wellKnownURI. To point the agent
    at a new discovery URL (e.g. its old host rotated or 404s), send a JSON body
    `{"wellKnownURI": "https://new-host/.well-known/agent-card.json"}`. The new
    URL is fetched, validated, and persisted on success. With no body the
    existing URI is used (backward compatible).
    """
    _require_admin(x_admin_key)
    track_api_query("PUT /agents/{id}", agent_id=str(agent_id))

    agent_repo = AgentRepository(db)
    existing = await agent_repo.get_by_id(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Optionally accept a new wellKnownURI from the request body. Tolerate an
    # absent/empty/non-JSON body so a plain PUT (re-fetch existing) still works.
    new_uri = None
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            new_uri = body.get("wellKnownURI") or None

    existing_uri = str(existing.wellKnownURI)
    if new_uri and str(new_uri) != existing_uri:
        well_known_uri = str(new_uri)
        uri_errors = validate_well_known_uri(well_known_uri)
        if uri_errors:
            raise HTTPException(status_code=400, detail="; ".join(uri_errors))

        # Don't let a URI change collide with a *different* agent's record.
        uri_owner = await agent_repo.get_by_well_known_uri(well_known_uri)
        if uri_owner and uri_owner.id != agent_id:
            raise HTTPException(
                status_code=409,
                detail=f"That wellKnownURI is already registered to a different agent (id={uri_owner.id}).",
            )
        hostname = urlparse(well_known_uri).hostname or ""
        if hostname:
            host_owner = await agent_repo.get_by_host(hostname)
            if host_owner and host_owner.id != agent_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"An agent from this host is already registered: '{host_owner.name}' (id={host_owner.id}).",
                )
    else:
        well_known_uri = existing_uri

    agent_card, error = await fetch_agent_card(well_known_uri)
    if error:
        raise HTTPException(status_code=400, detail=f"Failed to fetch agent card: {error}")
    if agent_card is None:
        raise HTTPException(status_code=500, detail="Internal error: agent card fetch returned no data")

    agent_data = _agent_create_from_card(
        agent_card, well_known_uri, author_fallback=existing.author,
    )

    try:
        await agent_repo.update(agent_id, agent_data)
        result = await agent_repo.get_by_id(agent_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {e}")


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: UUID, x_admin_key: Optional[str] = Header(default=None)):
    """Delete an agent (admin only)."""
    _require_admin(x_admin_key)
    track_api_query("DELETE /agents/{id}", agent_id=str(agent_id))

    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await agent_repo.delete(agent_id)
    return JSONResponse(status_code=204, content={})


# ============================================================================
# Health Check Endpoints
# ============================================================================


@router.get("/agents/{agent_id}/health", response_model=HealthStatus)
async def get_agent_health(agent_id: UUID):
    """Get current health status for an agent (last 24 hours)"""
    track_api_query("GET /agents/{id}/health", agent_id=str(agent_id))

    health_repo = HealthCheckRepository(db)
    status = await health_repo.get_health_status(agent_id)

    if not status:
        raise HTTPException(status_code=404, detail="No health check data available")

    return status


@router.get("/agents/{agent_id}/uptime", response_model=UptimeMetrics)
async def get_agent_uptime(agent_id: UUID, period_days: int = 30):
    """Get historical uptime metrics for an agent"""
    track_api_query("GET /agents/{id}/uptime", agent_id=str(agent_id), period_days=period_days)

    # Validate period
    if period_days > 90:
        period_days = 90

    health_repo = HealthCheckRepository(db)
    metrics = await health_repo.get_uptime_metrics(agent_id, period_days)

    if not metrics:
        raise HTTPException(status_code=404, detail="No uptime data available")

    return metrics


# ============================================================================
# Stats Endpoints
# ============================================================================


@router.get("/stats", response_model=RegistryStats)
async def get_registry_stats():
    """Get registry-wide statistics"""
    track_api_query("GET /stats")

    stats_repo = StatsRepository(db)
    return await stats_repo.get_registry_stats()


# ============================================================================
# Moderation Endpoints
# ============================================================================


@router.post("/agents/{agent_id}/flag", status_code=201)
@limiter.limit("5/hour")
async def flag_agent(agent_id: UUID, flag: AgentFlag, request: Request):
    """Community flag/report an agent"""
    track_api_query("POST /agents/{id}/flag", agent_id=str(agent_id))

    client_ip = request.client.host if request.client else None

    flag_repo = FlagRepository(db)
    await flag_repo.create_flag(agent_id, flag.reason.value, client_ip, flag.details)

    agent_repo = AgentRepository(db)
    await agent_repo.increment_flag_count(agent_id)

    return {"message": "Flag recorded"}


# ============================================================================
# Chat Proxy Endpoint
# ============================================================================


class ChatRequest(BaseModel):
    message: str
    context_id: Optional[str] = None


_BLOCKED_HOSTS = frozenset({
    "localhost",
    "metadata.google.internal",
    "metadata.google",
    "kubernetes.default.svc",
})

_BLOCKED_SUFFIXES = (".internal", ".local", ".svc", ".cluster.local")


def _is_private_url(url: str) -> bool:
    """Return True if the URL resolves to a private/internal address (SSRF guard)."""
    try:
        host = urlparse(url).hostname or ""
        addr = ipaddress.ip_address(host)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except ValueError:
        # hostname — block well-known internal names
        return host in _BLOCKED_HOSTS or any(host.endswith(s) for s in _BLOCKED_SUFFIXES)


def _client_target_url(client) -> Optional[str]:
    """The URL the SDK client's transport will POST to, or None if it can't be
    determined.

    Used to re-run the SSRF guard against the actual send target after the card
    is (re)fetched at chat time. Callers MUST fail closed on None: if we can't
    read the target a future SDK change could hide from us, we must not send,
    rather than fall back to a stale guard.
    """
    transport = getattr(client, "_transport", None) or getattr(client, "transport", None)
    return getattr(transport, "url", None) if transport else None


def _extract_text_from_parts(parts) -> str:
    """Join text content from a list of Part messages."""
    return "".join(p.text for p in parts if p.text)


def _extract_text(result) -> str:
    """Extract text from a StreamResponse."""
    if isinstance(result, Message):
        return _extract_text_from_parts(result.parts)
    if isinstance(result, Task):
        # Check artifacts first
        if result.artifacts:
            text = "".join(
                _extract_text_from_parts(artifact.parts)
                for artifact in result.artifacts
            )
            if text:
                return text
        # Fallback: status message
        if result.status.HasField("message"):
            text = _extract_text_from_parts(result.status.message.parts)
            if text:
                return text
        # Fallback: last agent message in history
        if result.history:
            for msg in reversed(result.history):
                if msg.role == Role.ROLE_AGENT:
                    text = _extract_text_from_parts(msg.parts)
                    if text:
                        return text
        return f"Task {TaskState.Name(result.status.state)}"
    return "No response"


@router.post("/agents/{agent_id}/chat")
@limiter.limit("30/minute")
async def chat_with_agent(agent_id: UUID, body: ChatRequest, request: Request):
    """Proxy a chat message to an agent via the a2a-sdk."""
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if _is_private_url(str(agent.url)):
        raise HTTPException(status_code=400, detail="Agent URL is not publicly reachable")

    context_id = body.context_id or str(uuid.uuid4())
    message = Message(
        message_id=str(uuid.uuid4()),
        context_id=context_id,
        role=Role.ROLE_USER,
        parts=[Part(text=body.message)],
    )

    health_repo = HealthCheckRepository(db)
    start = time.monotonic()
    try:
        # Build the client from the agent's *card*, not the wellKnownURI host.
        # Many agents publish their card on a public domain but run the actual
        # A2A handler elsewhere (Cloudflare Workers, etc.); the card's `url`
        # (mapped by parse_agent_card into supportedInterfaces[0].url) is the
        # real endpoint. Deriving the base from the wellKnownURI host instead
        # sent JSON-RPC POSTs to the wrong host and 502'd (#135).
        #
        # The card is refetched from the agent's stored, already-validated
        # wellKnownURI — never from request-controlled input.
        card_dict, card_error = await fetch_agent_card(str(agent.wellKnownURI))
        if card_error or card_dict is None:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            detail = f"Could not load agent card: {card_error or 'no data'}"
            await health_repo.create(agent_id, 502, elapsed_ms, False, detail, source='chat')
            raise HTTPException(status_code=502, detail=detail)

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            factory = ClientFactory(
                ClientConfig(httpx_client=http_client, streaming=False),
            )
            client = factory.create(parse_agent_card(card_dict))

            # SSRF guard on the ACTUAL send target. The stored agent.url was
            # checked above, but #135 refetches the card at chat time, so the
            # transport may target a different (freshly parsed) url. Re-check it
            # so a card that rotated to a private/internal address (127.0.0.1,
            # the GCP metadata host, etc.) can't be used to pivot.
            #
            # Fail closed: if we can't read the actual target (None), reject
            # rather than send — a future SDK that hides the transport url must
            # not silently bypass this guard.
            target_url = _client_target_url(client)
            if target_url is None or _is_private_url(target_url):
                elapsed_ms = int((time.monotonic() - start) * 1000)
                await health_repo.create(
                    agent_id, 400, elapsed_ms, False,
                    "Agent endpoint is not publicly reachable", source='chat',
                )
                raise HTTPException(status_code=400, detail="Agent endpoint is not publicly reachable")

            send_request = SendMessageRequest(message=message)
            response_text = ""
            async for event in client.send_message(send_request):
                if event.HasField("task"):
                    response_text = _extract_text(event.task)
                elif event.HasField("message"):
                    response_text = _extract_text(event.message)
            response_text = response_text or "No response"
    except httpx.TimeoutException:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        await health_repo.create(agent_id, 504, elapsed_ms, False, "Agent request timed out", source='chat')
        raise HTTPException(status_code=504, detail="Agent request timed out")
    except httpx.HTTPStatusError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        code = exc.response.status_code
        try:
            phrase = HTTPStatus(code).phrase
        except ValueError:
            phrase = "Unknown"
        error_msg = f"Agent returned {code} {phrase}"
        await health_repo.create(agent_id, code, elapsed_ms, False, error_msg, source='chat')
        raise HTTPException(status_code=code, detail=error_msg)
    except httpx.RequestError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        await health_repo.create(agent_id, 502, elapsed_ms, False, "Agent unreachable", source='chat')
        raise HTTPException(status_code=502, detail=f"Agent unreachable: {exc}")
    except HTTPException:
        # Already-formed HTTP errors (e.g. card-load failure above) carry their
        # own status/detail and a health row was already recorded — re-raise as-is.
        raise
    except Exception:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception("chat_proxy_error", agent_id=str(agent_id))
        await health_repo.create(agent_id, 502, elapsed_ms, False, "Agent returned an unexpected error", source='chat')
        raise HTTPException(status_code=502, detail="Agent returned an unexpected error")

    return {"response": response_text, "context_id": context_id}


# ============================================================================
# Admin Endpoints
# ============================================================================


def _require_admin(x_admin_key: Optional[str]):
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")


class MaintainerNotesUpdate(BaseModel):
    notes: Optional[str] = None


@router.patch("/agents/{agent_id}/notes", status_code=200)
async def update_maintainer_notes(
    agent_id: UUID,
    body: MaintainerNotesUpdate,
    x_admin_key: Optional[str] = Header(default=None),
):
    """Set or clear maintainer notes for an agent (admin only). Supports markdown."""
    _require_admin(x_admin_key)

    agent_repo = AgentRepository(db)
    updated = await agent_repo.update_maintainer_notes(agent_id, body.notes)
    if not updated:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Maintainer notes updated", "maintainer_notes": body.notes}


@router.get("/admin/flags")
async def list_flags(x_admin_key: Optional[str] = Header(default=None), limit: int = 100, offset: int = 0):
    """List all agent flags (admin only)"""
    _require_admin(x_admin_key)
    flag_repo = FlagRepository(db)
    flags = await flag_repo.list_flags(limit=limit, offset=offset)
    return {"flags": [f.model_dump(mode="json") for f in flags]}


# ============================================================================
# Mount router at both / and /api prefixes for GKE Gateway compatibility
# ============================================================================

# Include router at root (for direct access and docker-compose)
app.include_router(router)

# Include router at /api prefix (for GKE Gateway HTTPRoute)
app.include_router(router, prefix="/api")

# MCP is mounted dynamically inside lifespan() to get a fresh instance each time


# ============================================================================
# AI Discoverability Endpoints
# ============================================================================


@app.get("/.well-known/ai-plugin.json", include_in_schema=False)
async def ai_plugin():
    """OpenAI plugin manifest for AI system auto-discovery"""
    return {
        "schema_version": "v1",
        "name_for_human": "A2A Registry",
        "name_for_model": "a2a_registry",
        "description_for_human": "Community-driven directory of AI agents implementing the A2A Protocol.",
        "description_for_model": (
            "Search and discover AI agents that implement the A2A (Agent-to-Agent) Protocol. "
            "You can list agents, filter by skill or capability, search by keyword, and retrieve "
            "detailed agent cards including endpoints, supported modes, and conformance status. "
            "Agents self-register via a REST API and are health-checked every 30 minutes."
        ),
        "auth": {"type": "none"},
        "api": {
            "type": "openapi",
            "url": "https://a2aregistry.org/api/openapi.json",
        },
        "logo_url": "https://a2aregistry.org/logo.png",
        "contact_email": "hello@a2aregistry.org",
        "legal_info_url": "https://a2aregistry.org",
    }


@app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
async def llms_txt():
    """Plain-text description of the registry for LLMs that crawl for context"""
    return """\
# A2A Registry

A2A Registry (https://a2aregistry.org) is a live, public directory of AI agents
that implement the A2A (Agent-to-Agent) Protocol — an open standard for
interoperable AI agent communication.

## What is the A2A Protocol?

The A2A Protocol defines a standard way for AI agents to advertise their
capabilities, accept tasks, and communicate with each other. Each agent publishes
an "agent card" at a well-known URI (e.g. https://example.com/.well-known/agent.json)
describing its name, description, skills, supported input/output modes, and
A2A capabilities (streaming, push notifications, state transition history).

## Registry API

Base URL: https://a2aregistry.org/api

### Key Endpoints

- GET  /agents              List/search agents (params: search, skill, capability, author, conformance, healthy, limit, offset)
- GET  /agents/{id}         Get a single agent by UUID (includes health metrics, maintainer notes)
- POST /agents/register     Register an agent by providing its wellKnownURI
- GET  /agents/{id}/health  Current health status (last 24 hours)
- GET  /agents/{id}/uptime  Historical uptime metrics
- GET  /agents/{id}/chat    Send a message to an agent via the A2A chat proxy
- GET  /stats               Registry-wide statistics (total agents, trending skills, health %)

### Filtering

- ?search=<keyword>         Full-text search across name, description, author, skill names, and skill tags
- ?skill=<skill-id>         Filter agents that have a specific skill tag
- ?capability=streaming     Filter by A2A capability (streaming | pushNotifications | stateTransitionHistory)
- ?conformance=standard     Only strict A2A spec-compliant agents
- ?conformance=non-standard Non-conformant or unvalidated agents
- ?healthy=true             Only agents that passed their last health check

### OpenAPI / Interactive Docs

Full OpenAPI spec: https://a2aregistry.org/api/openapi.json
Interactive docs:  https://a2aregistry.org/api/docs

## MCP Server

The registry also exposes an MCP (Model Context Protocol) server at:
  https://a2aregistry.org/mcp/

MCP tools available:
- search_agents(query, limit)                          Search agents by keyword
- list_agents(skill, capability, author, conformance)  List with filters
- get_agent(agent_id)                                  Get agent by UUID
- list_skills(limit)                                   List all skills by popularity
- get_registry_stats()                                 Registry-wide statistics

## Registering an Agent

POST https://a2aregistry.org/api/agents/register
Content-Type: application/json

{"wellKnownURI": "https://your-agent.example.com/.well-known/agent.json"}

The registry fetches the agent card automatically and validates A2A conformance.
Health checks run every 30 minutes.

## Conformance

- conformance: true  = strict A2A spec compliant (validated by the worker)
- conformance: false = non-conformant
- conformance: null  = not yet validated
"""


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found", "path": str(request.url)},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Custom 500 handler"""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )
