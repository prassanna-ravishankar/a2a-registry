"""FastAPI application - main entry point"""

from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import db
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
from .utils import fetch_agent_card, track_api_query, verify_well_known_uri


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    await db.connect()
    print("✅ Database connected")

    yield

    # Shutdown
    await db.disconnect()
    print("👋 Database disconnected")


app = FastAPI(
    title="A2A Registry API",
    description="Community-driven directory of AI agents using the A2A Protocol",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create router for all API endpoints
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
async def register_agent_simple(registration: AgentRegister, request: Request):
    """
    Register an agent by its wellKnownURI (simplified flow).

    Just provide the wellKnownURI and we'll fetch the agent card automatically.
    The agent card must be accessible and contain valid A2A Protocol fields.

    Example:
        POST /api/agents/register
        {"wellKnownURI": "https://example.com/.well-known/agent.json"}
    """
    well_known_uri = str(registration.wellKnownURI)
    track_api_query("POST /agents/register", wellKnownURI=well_known_uri)

    # Check if already exists
    agent_repo = AgentRepository(db)
    existing = await agent_repo.get_by_well_known_uri(well_known_uri)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Agent already registered. Use PUT /agents/{{id}} to update.",
        )

    # Fetch the agent card from the wellKnownURI
    agent_card, error = await fetch_agent_card(well_known_uri)
    if error:
        raise HTTPException(status_code=400, detail=f"Failed to fetch agent card: {error}")

    # Build AgentCreate from fetched agent card
    try:
        agent_data = AgentCreate(
            protocolVersion=agent_card.get("protocolVersion", "0.3.0"),
            name=agent_card["name"],
            description=agent_card["description"],
            author=registration.author or agent_card.get("provider", {}).get("organization", "Unknown"),
            wellKnownURI=well_known_uri,
            url=agent_card["url"],
            version=agent_card["version"],
            provider=agent_card.get("provider"),
            documentationUrl=agent_card.get("documentationUrl"),
            capabilities=agent_card.get("capabilities", {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False}),
            defaultInputModes=agent_card.get("defaultInputModes", ["text/plain"]),
            defaultOutputModes=agent_card.get("defaultOutputModes", ["text/plain"]),
            skills=agent_card.get("skills", []),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid agent card format: {e}")

    # Create agent
    try:
        created_agent = await agent_repo.create(agent_data)
        result = await agent_repo.get_by_id(created_agent.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {e}")


@router.post("/agents", response_model=AgentPublic, status_code=201)
async def register_agent_full(agent: AgentCreate, request: Request):
    """
    Register a new agent (full payload).

    Validates ownership by fetching wellKnownURI and comparing key fields.
    For a simpler flow, use POST /agents/register with just the wellKnownURI.
    """
    track_api_query("POST /agents", author=agent.author)

    # Check if already exists
    agent_repo = AgentRepository(db)
    existing = await agent_repo.get_by_well_known_uri(str(agent.wellKnownURI))
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Agent with wellKnownURI {agent.wellKnownURI} already exists",
        )

    # Verify ownership via wellKnownURI
    verified, message = await verify_well_known_uri(agent)
    if not verified:
        raise HTTPException(status_code=400, detail=f"Ownership verification failed: {message}")

    # Create agent
    try:
        created_agent = await agent_repo.create(agent)
        result = await agent_repo.get_by_id(created_agent.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {e}")


@router.get("/agents", response_model=PaginatedAgents)
async def list_agents(
    skill: Optional[str] = None,
    capability: Optional[str] = None,
    author: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List agents with optional filtering and pagination.

    Query parameters:
    - skill: Filter by skill ID
    - capability: Filter by A2A capability (e.g., "streaming")
    - author: Filter by author name (case-insensitive partial match)
    - limit: Max results to return (default: 50, max: 100)
    - offset: Pagination offset (default: 0)
    """
    track_api_query(
        "GET /agents",
        skill=skill,
        capability=capability,
        author=author,
        limit=limit,
        offset=offset,
    )

    # Validate limit
    if limit > 100:
        limit = 100

    agent_repo = AgentRepository(db)
    agents, total = await agent_repo.list_agents(
        skill=skill,
        capability=capability,
        author=author,
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


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: UUID, request: Request):
    """
    Delete an agent (owner only).

    Requires re-verification of wellKnownURI ownership.
    """
    track_api_query("DELETE /agents/{id}", agent_id=str(agent_id))

    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Re-verify ownership before deletion
    agent_create = AgentCreate(**agent.model_dump())
    verified, message = await verify_well_known_uri(agent_create)

    if not verified:
        raise HTTPException(
            status_code=403,
            detail=f"Ownership verification failed. Cannot delete. {message}",
        )

    # Soft delete
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
async def flag_agent(agent_id: UUID, flag: AgentFlag, request: Request):
    """Community flag/report an agent"""
    track_api_query("POST /agents/{id}/flag", agent_id=str(agent_id))

    # Get client IP
    client_ip = request.client.host if request.client else None

    # Record flag
    flag_repo = FlagRepository(db)
    await flag_repo.create_flag(agent_id, flag.reason, client_ip)

    # Increment flag count
    agent_repo = AgentRepository(db)
    await agent_repo.increment_flag_count(agent_id)

    return {"message": "Flag recorded"}


# ============================================================================
# Mount router at both / and /api prefixes for GKE Gateway compatibility
# ============================================================================

# Include router at root (for direct access and docker-compose)
app.include_router(router)

# Include router at /api prefix (for GKE Gateway HTTPRoute)
app.include_router(router, prefix="/api")


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
