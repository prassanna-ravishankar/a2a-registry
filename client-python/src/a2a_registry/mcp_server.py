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
    - Get ready-to-use code snippets for connecting to agents
    - View registry statistics

    The A2A protocol enables interoperable AI agent communication.
    When users ask about finding agents, AI agents, or the A2A registry,
    use the tools from this server to search and retrieve information.

    When users want to know HOW to use or connect to an agent, use the
    get_code_snippets tool to provide ready-to-use Python code examples.
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


@mcp.tool
def get_code_snippets(agent_id: str, snippet_type: str = "all") -> dict:
    """
    Get ready-to-use Python code snippets for connecting to and using an agent.

    This tool provides practical, copy-paste code examples showing how to:
    - Discover and connect to agents using the integrated A2A SDK
    - Use the registry client for discovery only
    - Implement low-level A2A protocol interactions
    - Search and filter agents
    - Use advanced filtering features

    Args:
        agent_id: The agent's registry ID
        snippet_type: Type of snippet to return. Options:
                     - "all" (default): Returns all available code snippets
                     - "integrated": Quick 3-line discovery + invoke (recommended)
                     - "registry": Basic registry usage for discovery
                     - "a2a_official": Low-level A2A SDK interaction
                     - "search": Search and discovery examples
                     - "advanced": Advanced filtering and async usage

    Returns:
        Dictionary containing the requested code snippet(s) with installation instructions

    Use cases: "show me how to connect to this agent", "give me code to use agent X",
               "how do I invoke this agent"
    """
    agent = _registry.get_by_id(agent_id)
    if not agent:
        return {"error": f"Agent '{agent_id}' not found"}

    # Generate snippets similar to the website modals
    snippets = {}

    # Integrated approach (recommended)
    integrated = f"""# Integrated Discover → Invoke workflow
# Combine registry discovery with A2A SDK invocation
from a2a_registry import Registry

# Step 1: Discover agent
registry = Registry()
agent = registry.get_by_id("{agent.registry_id}")

# Step 2: Connect with one line!
client = agent.connect()

# Step 3: Invoke using A2A SDK
# Now use the official A2A SDK methods:
# - client.message.send(...)
# - client.message.stream(...)
# - client.tasks.get(...)

print(f"Connected to {{agent.name}}")
print(f"Ready to invoke skills: {{[s.id for s in agent.skills]}}")"""

    # Registry client only (discovery)
    registry = f"""# Install the A2A Registry Python client
# pip install a2a-registry-client

# Basic usage - find and connect to {agent.name}
from a2a_registry import Registry
import requests

registry = Registry()
agent = registry.get_by_id("{agent.registry_id}")
print(f"Found: {{agent.name}} - {{agent.description}}")

# Connect to the agent using URL from registry
response = requests.post(agent.url, json={{
    "jsonrpc": "2.0",
    "method": "hello",
    "params": {{}},
    "id": 1
}})
print(response.json())"""

    # Official A2A SDK (low-level)
    first_skill = agent.skills[0].id if agent.skills else "example-skill"
    a2a_official = f"""# Install the official A2A Python SDK
# pip install a2a-sdk

# Using official A2A SDK to interact with {agent.name}
import asyncio
import httpx
from uuid import uuid4
from a2a_registry import Registry
from a2a import A2ACardResolver, SendMessageRequest, MessageSendParams

async def interact_with_agent():
    # Get agent URL from registry
    registry = Registry()
    agent = registry.get_by_id("{agent.registry_id}")
    base_url = str(agent.url).rstrip('/')

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url
        )

        # Get agent capabilities
        agent_card = await resolver.resolve_card()
        print(f"Agent: {{agent_card.name}}")

        # Send a message to the agent
        send_message_payload = {{
            'message': {{
                'role': 'user',
                'parts': [
                    {{'kind': 'text', 'text': 'Hello! Can you help me?'}}
                ],
                'messageId': uuid4().hex,
            }}
        }}

        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**send_message_payload)
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

# Run the async example
asyncio.run(interact_with_agent())"""

    # Search and discovery
    skill_search = (
        f"agents = registry.find_by_skill('{first_skill}')"
        if agent.skills
        else f"agents = registry.search('{agent.name.lower().split()[0]}')"
    )
    search = f"""# Search for agents by capability or skill
from a2a_registry import Registry

registry = Registry()

# Search for agents with specific skills
{skill_search}
print(f"Found {{len(agents)}} agents")

# Find agents by capability
streaming_agents = registry.find_by_capability("streaming")
print(f"Streaming agents: {{len(streaming_agents)}}")"""

    # Advanced usage
    has_streaming = (
        agent.capabilities and agent.capabilities.streaming
        if hasattr(agent.capabilities, 'streaming')
        else False
    )
    skills_filter = f"skills=['{first_skill}']," if agent.skills else ""
    advanced = f"""# Advanced filtering and async usage
from a2a_registry import Registry, AsyncRegistry
import asyncio

# Synchronous filtering
registry = Registry()
filtered_agents = registry.filter_agents(
    {skills_filter}
    input_modes=["text/plain"],
    capabilities=["streaming"] if {has_streaming} else []
)

# Async usage for high-performance applications
async def async_example():
    async with AsyncRegistry() as registry:
        agents = await registry.get_all()
        stats = await registry.get_stats()
        print(f"Total agents: {{stats['total_agents']}}")

asyncio.run(async_example())"""

    # Build response based on snippet_type
    if snippet_type == "integrated":
        snippets["integrated"] = integrated
    elif snippet_type == "registry":
        snippets["registry"] = registry
    elif snippet_type == "a2a_official":
        snippets["a2a_official"] = a2a_official
    elif snippet_type == "search":
        snippets["search"] = search
    elif snippet_type == "advanced":
        snippets["advanced"] = advanced
    else:  # "all"
        snippets = {
            "integrated": integrated,
            "registry": registry,
            "a2a_official": a2a_official,
            "search": search,
            "advanced": advanced
        }

    return {
        "agent_id": agent.registry_id,
        "agent_name": agent.name,
        "snippets": snippets,
        "installation": {
            "recommended": "pip install \"a2a-registry-client[a2a]\"",
            "basic": "pip install a2a-registry-client",
            "with_async": "pip install \"a2a-registry-client[async]\"",
            "all_features": "pip install \"a2a-registry-client[all]\""
        },
        "documentation": "https://github.com/prassanna-ravishankar/a2a-registry/blob/main/MCP_INTEGRATION.md"
    }


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
