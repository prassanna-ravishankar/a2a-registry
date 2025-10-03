"""
A2A Registry MCP Server

Model Context Protocol server for the A2A Registry.
Provides tools for discovering and querying AI agents.
"""

from typing import List, Optional
from fastmcp import FastMCP
from .client import Registry
from .models import Agent

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
    - View registry statistics

    The A2A protocol enables interoperable AI agent communication.
    When users ask about finding agents, AI agents, or the A2A registry,
    use the tools from this server to search and retrieve information.
    """
)

# Global registry instance (with caching)
_registry = Registry()


def _format_agent(agent: Agent) -> dict:
    """Format an agent for MCP response."""
    # Combine registryTags and legacy tags
    all_tags = []
    if agent.registryTags:
        all_tags.extend(agent.registryTags)
    if agent.tags:
        all_tags.extend(agent.tags)

    return {
        "id": agent.registry_id,
        "name": agent.name,
        "description": agent.description,
        "author": agent.author,
        "url": str(agent.url) if agent.url else None,
        "wellKnownURI": str(agent.wellKnownURI),
        "capabilities": agent.capabilities.model_dump() if agent.capabilities else {},
        "skills": [skill.model_dump() for skill in agent.skills],
        "defaultInputModes": agent.defaultInputModes or [],
        "defaultOutputModes": agent.defaultOutputModes or [],
        "protocolVersion": agent.protocolVersion,
        "tags": list(set(all_tags)),  # Deduplicate tags
        "version": agent.version,
        "provider": agent.provider.model_dump() if agent.provider else None,
        "homepage": str(agent.homepage) if agent.homepage else None,
        "repository": str(agent.repository) if agent.repository else None,
        "apiEndpoint": str(agent.apiEndpoint) if agent.apiEndpoint else None,
        "documentationUrl": str(agent.documentationUrl) if agent.documentationUrl else None,
        "iconUrl": str(agent.iconUrl) if agent.iconUrl else None,
    }


def _format_agents(agents: List[Agent]) -> List[dict]:
    """Format a list of agents for MCP response."""
    return [_format_agent(agent) for agent in agents]


@mcp.tool
def search_agents(query: str) -> List[dict]:
    """
    Search for AI agents in the A2A Registry by text query.

    Use this when the user wants to find agents by keyword, topic, or general description.
    Searches across agent names, descriptions, and skills.

    Args:
        query: Search query string (e.g., "translation", "image generation", "data analysis")

    Returns:
        List of agents matching the search query with their details

    Example queries: "translation agents", "agents that can generate images", "data processing"
    """
    agents = _registry.search(query)
    return _format_agents(agents)


@mcp.tool
def get_agent(agent_id: str) -> Optional[dict]:
    """
    Get a specific agent by its registry ID.

    Args:
        agent_id: The agent's registry ID (typically in format: author/agent-name)

    Returns:
        Agent details if found, None otherwise
    """
    agent = _registry.get_by_id(agent_id)
    return _format_agent(agent) if agent else None


@mcp.tool
def find_by_capability(capability: str) -> List[dict]:
    """
    Find AI agents that support a specific A2A protocol capability.

    Use this when the user asks for agents with specific technical features like
    streaming responses, push notifications, or other A2A capabilities.

    Args:
        capability: Capability name - common values include:
                   "streaming" - real-time streaming responses
                   "pushNotifications" - server-initiated notifications
                   "stateTransitionHistory" - conversation state tracking
                   "contextWindow" - context management

    Returns:
        List of agents that have the specified capability enabled

    Use cases: "find agents with streaming", "which agents support push notifications"
    """
    agents = _registry.find_by_capability(capability)
    return _format_agents(agents)


@mcp.tool
def find_by_skill(skill_id: str) -> List[dict]:
    """
    Find agents that have a specific skill.

    Args:
        skill_id: The skill ID to search for

    Returns:
        List of agents with the specified skill
    """
    agents = _registry.find_by_skill(skill_id)
    return _format_agents(agents)


@mcp.tool
def find_by_author(author: str) -> List[dict]:
    """
    Find all agents created by a specific author.

    Args:
        author: Author name to search for

    Returns:
        List of agents by the specified author
    """
    agents = _registry.find_by_author(author)
    return _format_agents(agents)


@mcp.tool
def filter_agents(
    skills: Optional[List[str]] = None,
    capabilities: Optional[List[str]] = None,
    input_modes: Optional[List[str]] = None,
    output_modes: Optional[List[str]] = None,
    authors: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    protocol_version: Optional[str] = None
) -> List[dict]:
    """
    Advanced filtering of agents with multiple criteria (AND logic).

    Args:
        skills: List of required skill IDs (agent must have ALL)
        capabilities: List of required A2A capabilities (agent must have ALL enabled)
        input_modes: List of required input MIME types (agent must support ALL)
        output_modes: List of required output MIME types (agent must support ALL)
        authors: List of acceptable authors (agent must match ONE)
        tags: List of required tags (agent must have ALL)
        protocol_version: Required A2A protocol version (exact match)

    Returns:
        List of agents matching ALL specified criteria
    """
    agents = _registry.filter_agents(
        skills=skills,
        capabilities=capabilities,
        input_modes=input_modes,
        output_modes=output_modes,
        authors=authors,
        tags=tags,
        protocol_version=protocol_version
    )
    return _format_agents(agents)


@mcp.tool
def list_all_agents() -> List[dict]:
    """
    Get all AI agents in the A2A Registry.

    Use this when the user wants to see all available agents, browse the registry,
    or get a complete list of agents without filtering.

    Returns:
        List of all registered agents with their details (name, description, capabilities, etc.)

    Use cases: "show me all agents", "list available agents", "what agents are in the registry"
    """
    agents = _registry.get_all()
    return _format_agents(agents)


@mcp.tool
def get_registry_stats() -> dict:
    """
    Get statistics and overview of the A2A Registry.

    Use this when the user asks about registry information, how many agents exist,
    what capabilities are available, or wants a summary of the registry.

    Returns:
        Dictionary with statistics including:
        - Total agent count
        - Available capabilities and their usage
        - Protocol versions
        - Other aggregate metrics

    Use cases: "how many agents are there?", "what are the registry stats?", "give me an overview"
    """
    return _registry.get_stats()


@mcp.tool
def list_capabilities() -> List[str]:
    """
    List all A2A protocol capabilities available across agents.

    Returns:
        List of unique capability names found in the registry
    """
    stats = _registry.get_stats()
    return list(stats.get("capabilities_count", {}).keys())


@mcp.tool
def find_by_input_mode(input_mode: str) -> List[dict]:
    """
    Find agents that support a specific input mode.

    Args:
        input_mode: Input MIME type (e.g., "text/plain", "image/jpeg", "audio/mpeg")

    Returns:
        List of agents supporting the input mode
    """
    agents = _registry.find_by_input_mode(input_mode)
    return _format_agents(agents)


@mcp.tool
def find_by_output_mode(output_mode: str) -> List[dict]:
    """
    Find agents that support a specific output mode.

    Args:
        output_mode: Output MIME type (e.g., "text/plain", "application/json", "image/png")

    Returns:
        List of agents supporting the output mode
    """
    agents = _registry.find_by_output_mode(output_mode)
    return _format_agents(agents)


@mcp.tool
def refresh_registry() -> dict:
    """
    Force refresh the registry cache to get latest data.

    Returns:
        Status message indicating cache was refreshed
    """
    _registry.refresh()
    return {"status": "success", "message": "Registry cache refreshed"}


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
