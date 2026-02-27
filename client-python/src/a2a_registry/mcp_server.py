"""
A2A Registry MCP Server

Model Context Protocol server for the A2A Registry.
Provides tools for discovering and querying AI agents from the live API.
"""

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .api_client import APIRegistry

# Initialize the MCP server
mcp = FastMCP(
    "A2A Registry",
    instructions="""
    This server provides access to the A2A (Agent-to-Agent) Registry,
    a public directory of AI agents that support the A2A protocol.

    Use this server to:
    - Search and discover AI agents
    - Find agents with specific capabilities (streaming, push notifications, etc.)
    - Filter agents by skills, authors, input/output modes, or tags
    - Get detailed information about specific agents
    - Get ready-to-use code snippets for connecting to agents
    - View registry statistics

    The A2A protocol enables interoperable AI agent communication.
    When users ask about finding agents, AI agents, or the A2A registry,
    use the tools from this server to search and retrieve information.

    When users want to know HOW to use or connect to an agent, use the
    get_connection_snippet tool to provide ready-to-use Python code examples.
    """
)

# Global registry instance (with caching)
_registry = APIRegistry()


def _format_agent(agent) -> dict:
    """Format an agent for MCP response."""
    return {
        "id": str(agent.id) if agent.id else None,
        "name": agent.name,
        "description": agent.description,
        "author": agent.author,
        "url": str(agent.url) if agent.url else None,
        "wellKnownURI": str(agent.wellKnownURI) if agent.wellKnownURI else None,
        "capabilities": agent.capabilities.model_dump() if hasattr(agent, "capabilities") and agent.capabilities else {},
        "skills": [s.model_dump() for s in (agent.skills or [])],
        "defaultInputModes": agent.defaultInputModes or [],
        "defaultOutputModes": agent.defaultOutputModes or [],
        "protocolVersion": getattr(agent, "protocolVersion", None),
        "version": getattr(agent, "version", None),
        "provider": agent.provider.model_dump() if hasattr(agent, "provider") and agent.provider else None,
        "documentationUrl": str(agent.documentationUrl) if hasattr(agent, "documentationUrl") and agent.documentationUrl else None,
        "is_healthy": getattr(agent, "is_healthy", None),
        "uptime_percentage": getattr(agent, "uptime_percentage", None),
    }


@mcp.tool
def search_agents(query: str) -> List[dict]:
    """
    Search for AI agents in the A2A Registry by text query.

    Searches across agent names, descriptions, and skills. Use this when
    users want to find agents by keyword, topic, or general description.

    Args:
        query: Search query string (e.g., "translation", "image generation", "data analysis")

    Returns:
        List of matching agents with their details
    """
    query_lower = query.lower()
    all_agents = _registry.get_all()
    results = []
    for agent in all_agents:
        if (query_lower in agent.name.lower()
                or query_lower in agent.description.lower()
                or any(query_lower in s.name.lower() or query_lower in s.description.lower()
                       for s in (agent.skills or []))):
            results.append(agent)
    return [_format_agent(a) for a in results]


@mcp.tool
def get_agent(agent_id: str) -> Optional[dict]:
    """
    Get a specific agent by its UUID.

    Args:
        agent_id: The agent's UUID (from list_all_agents or search_agents)

    Returns:
        Agent details if found, None otherwise
    """
    agent = _registry.get_by_id(agent_id)
    return _format_agent(agent) if agent else None


@mcp.tool
def find_by_capability(capability: str) -> List[dict]:
    """
    Find AI agents that support a specific A2A protocol capability.

    Args:
        capability: One of: "streaming", "pushNotifications", "stateTransitionHistory"

    Returns:
        List of agents with the capability enabled
    """
    agents = _registry.find_by_capability(capability)
    return [_format_agent(a) for a in agents]


@mcp.tool
def find_by_skill(skill_id: str) -> List[dict]:
    """
    Find agents that have a specific skill.

    Args:
        skill_id: The skill ID to search for (e.g., "weather-forecast")

    Returns:
        List of agents with the specified skill
    """
    agents = _registry.find_by_skill(skill_id)
    return [_format_agent(a) for a in agents]


@mcp.tool
def find_by_author(author: str) -> List[dict]:
    """
    Find all agents created by a specific author.

    Args:
        author: Author name (partial match, case-insensitive)

    Returns:
        List of agents by the specified author
    """
    agents = _registry.find_by_author(author)
    return [_format_agent(a) for a in agents]


@mcp.tool
def list_all_agents(limit: int = 100) -> List[dict]:
    """
    Get all AI agents in the A2A Registry.

    Args:
        limit: Maximum number of agents to return (default 100, max 1000)

    Returns:
        List of all registered agents with their details
    """
    agents = _registry.get_all(limit=min(limit, 1000))
    return [_format_agent(a) for a in agents]


@mcp.tool
def get_registry_stats() -> dict:
    """
    Get statistics and overview of the A2A Registry.

    Returns:
        Dictionary with total agents, healthy count, health %, skills count, etc.
    """
    return _registry.get_stats()


@mcp.tool
def list_capabilities() -> List[str]:
    """
    List all A2A protocol capabilities tracked in the registry.

    Returns:
        List of valid capability names
    """
    return ["streaming", "pushNotifications", "stateTransitionHistory"]


@mcp.tool
def refresh_registry() -> dict:
    """
    Force refresh the registry cache to get latest data.

    Returns:
        Status message
    """
    _registry.clear_cache()
    return {"status": "success", "message": "Registry cache cleared — next query will fetch fresh data"}


@mcp.tool
def get_connection_snippet(agent_id: str) -> dict:
    """
    Get a ready-to-use Python code snippet for connecting to a specific agent.

    Args:
        agent_id: The agent's UUID

    Returns:
        Dict with code snippets and installation instructions
    """
    agent = _registry.get_by_id(agent_id)
    if not agent:
        return {"error": f"Agent '{agent_id}' not found"}

    registry_snippet = f"""from a2a_registry import APIRegistry

registry = APIRegistry()
agent = registry.get_by_id("{agent.id}")
print(f"Found: {{agent.name}}")
"""

    a2a_snippet = f"""import asyncio
import httpx
from a2a import A2ACardResolver

async def main():
    async with httpx.AsyncClient() as client:
        resolver = A2ACardResolver(
            httpx_client=client,
            base_url="{agent.url}"
        )
        card = await resolver.resolve_card()
        print(f"Connected to {{card.name}}")

asyncio.run(main())
"""

    curl_snippet = f"""curl -X POST {agent.url} \\
  -H "Content-Type: application/json" \\
  -d '{{
    "jsonrpc": "2.0",
    "method": "hello",
    "params": {{}},
    "id": 1
  }}'"""

    return {
        "agent_id": str(agent.id),
        "agent_name": agent.name,
        "snippets": {
            "python_registry": registry_snippet,
            "python_a2a_sdk": a2a_snippet,
            "curl": curl_snippet,
        },
        "installation": {
            "basic": "pip install a2a-registry-client",
            "with_a2a_sdk": 'pip install "a2a-registry-client[a2a]"',
        },
    }


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
