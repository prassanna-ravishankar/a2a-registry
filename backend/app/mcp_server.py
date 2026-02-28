"""MCP server for the A2A Registry — mounted at /mcp in the FastAPI app."""

from typing import Optional

from fastmcp import FastMCP

from .database import db
from .repositories import AgentRepository, StatsRepository

mcp = FastMCP(
    "A2A Registry",
    instructions="""
    This server provides access to the A2A (Agent-to-Agent) Registry,
    a public directory of AI agents that support the A2A protocol.

    Use this server to:
    - Search and discover AI agents by keyword, skill, capability, or author
    - Filter by A2A conformance (standard vs non-standard)
    - Get detailed information about specific agents
    - View registry statistics

    The A2A protocol enables interoperable AI agent communication.
    """,
)


def _format_agent(agent) -> dict:
    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "author": agent.author,
        "url": str(agent.url) if agent.url else None,
        "wellKnownURI": str(agent.wellKnownURI) if agent.wellKnownURI else None,
        "version": agent.version,
        "conformance": agent.conformance,
        "capabilities": agent.capabilities.model_dump() if agent.capabilities else {},
        "skills": [s.model_dump() for s in (agent.skills or [])],
        "defaultInputModes": agent.defaultInputModes or [],
        "defaultOutputModes": agent.defaultOutputModes or [],
        "provider": agent.provider.model_dump() if agent.provider else None,
        "is_healthy": agent.is_healthy,
        "uptime_percentage": agent.uptime_percentage,
    }


@mcp.tool
async def search_agents(query: str, limit: int = 20) -> list[dict]:
    """
    Search for AI agents by keyword across name, description, and author.

    Args:
        query: Search query (e.g. "translation", "data analysis", "weather")
        limit: Max results (default 20)
    """
    repo = AgentRepository(db)
    agents, _ = await repo.list_agents(search=query, limit=min(limit, 100))
    return [_format_agent(a) for a in agents]


@mcp.tool
async def list_agents(
    skill: Optional[str] = None,
    capability: Optional[str] = None,
    author: Optional[str] = None,
    conformance: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    List agents with optional filters.

    Args:
        skill: Filter by skill tag (e.g. "search", "nlp")
        capability: Filter by A2A capability ("streaming", "pushNotifications", "stateTransitionHistory")
        author: Filter by author name (partial match)
        conformance: "standard" (A2A spec compliant) or "non-standard"
        limit: Max results (default 20)
        offset: Pagination offset
    """
    if conformance not in (None, "standard", "non-standard"):
        conformance = None
    repo = AgentRepository(db)
    agents, total = await repo.list_agents(
        skill=skill,
        capability=capability,
        author=author,
        conformance=conformance,
        limit=min(limit, 100),
        offset=offset,
    )
    return {"agents": [_format_agent(a) for a in agents], "total": total, "limit": limit, "offset": offset}


@mcp.tool
async def get_agent(agent_id: str) -> Optional[dict]:
    """
    Get a specific agent by UUID.

    Args:
        agent_id: The agent's UUID
    """
    from uuid import UUID
    try:
        uid = UUID(agent_id)
    except ValueError:
        return None
    repo = AgentRepository(db)
    agent = await repo.get_by_id(uid)
    return _format_agent(agent) if agent else None


@mcp.tool
async def get_registry_stats() -> dict:
    """Get registry-wide statistics: total agents, health %, trending skills, etc."""
    repo = StatsRepository(db)
    stats = await repo.get_registry_stats()
    return stats.model_dump()


@mcp.tool
async def list_skills(limit: int = 50) -> list[dict]:
    """
    List all unique skills available across registered agents, ordered by agent count.

    Returns skill IDs and how many agents offer each skill — useful for discovering
    what capabilities are available in the registry before filtering agents by skill.

    Args:
        limit: Max number of skills to return (default 50)
    """
    rows = await db.fetch(
        """
        SELECT
            skill_id,
            COUNT(*) as agent_count
        FROM (
            SELECT jsonb_array_elements(skills) ->> 'id' as skill_id
            FROM agents
            WHERE hidden = false AND skills != '[]'::jsonb
        ) s
        WHERE skill_id IS NOT NULL
        GROUP BY skill_id
        ORDER BY agent_count DESC
        LIMIT $1
        """,
        min(limit, 200),
    )
    return [{"skill": row["skill_id"], "agent_count": row["agent_count"]} for row in rows]
