# A2A Registry Python Client

Official Python client library for the A2A Registry - a community-driven directory of AI agents.

## Installation

```bash
pip install a2a-registry-client

# For async support:
pip install "a2a-registry-client[async]"

# For A2A SDK integration (discover + invoke agents):
pip install "a2a-registry-client[a2a]"

# For all features:
pip install "a2a-registry-client[all]"
```

## Quick Start

```python
from a2a_registry import Registry

# Initialize the registry client
registry = Registry()

# Get all agents
agents = registry.get_all()
for agent in agents:
    print(f"{agent.name} - {agent.description}")

# Find agents by skill
weather_agents = registry.find_by_skill("weather-forecast")

# Find agents by capability
streaming_agents = registry.find_by_capability("streaming")

# Search agents by text
search_results = registry.search("translation")
```

## Features

- Simple, intuitive API
- Automatic caching for better performance
- Type hints and full typing support
- Comprehensive search and filtering options
- Lightweight with minimal dependencies

## API Reference

### Registry Class

#### `get_all() -> List[Agent]`
Retrieve all agents from the registry.

#### `find_by_skill(skill_id: str) -> List[Agent]`
Find agents that have a specific skill.

#### `find_by_capability(capability: str) -> List[Agent]`
Find agents with a specific A2A protocol capability (e.g., "streaming", "pushNotifications").

#### `find_by_author(author: str) -> List[Agent]`
Find all agents by a specific author.

#### `search(query: str) -> List[Agent]`
Search agents by text across name, description, and skills.

#### `get_by_id(agent_id: str) -> Optional[Agent]`
Get a specific agent by its ID.

### Agent Model

```python
class Agent:
    name: str
    description: str
    author: str
    wellKnownURI: str
    skills: List[Skill]
    capabilities: Optional[Capabilities]
    version: Optional[str]
    registryTags: Optional[List[str]]
    documentationUrl: Optional[str]
    # ... additional fields
```

### Skill Model

```python
class Skill:
    id: str
    name: str
    description: str
    tags: Optional[List[str]]
    inputModes: Optional[List[str]]
    outputModes: Optional[List[str]]
```

## Examples

### Finding Translation Agents

```python
from a2a_registry import Registry

registry = Registry()

# Find agents with translation skills
translators = registry.find_by_skill("translation")

for agent in translators:
    print(f"Agent: {agent.name}")
    print(f"Author: {agent.author}")
    for skill in agent.skills:
        if "translation" in skill.id.lower():
            print(f"  Skill: {skill.name} - {skill.description}")
```

### Filtering by Multiple Criteria

```python
from a2a_registry import Registry

registry = Registry()

# Get all agents
all_agents = registry.get_all()

# Filter for agents that support streaming and have specific skills
filtered = [
    agent for agent in all_agents
    if agent.capabilities and agent.capabilities.streaming
    and any(s.id == "real-time-data" for s in agent.skills)
]
```

## Advanced Features

### Input/Output Mode Filtering

```python
# Find agents that accept specific input types
text_agents = registry.find_by_input_mode("text/plain")
image_agents = registry.find_by_input_mode("image/jpeg")

# Find agents that produce specific output types
json_agents = registry.find_by_output_mode("application/json")

# Find agents with both specific input AND output modes
versatile_agents = registry.find_by_modes(
    input_mode="text/plain",
    output_mode="application/json"
)

# Discover all available modes
input_modes = registry.get_available_input_modes()
output_modes = registry.get_available_output_modes()
```

### Multi-Criteria Filtering

```python
# Advanced filtering with multiple criteria
filtered_agents = registry.filter_agents(
    skills=["text-generation", "summarization"],
    capabilities=["streaming", "pushNotifications"],
    input_modes=["text/plain"],
    output_modes=["application/json"],
    authors=["OpenAI", "Anthropic"],
    tags=["production-ready"],
    protocol_version="1.0"
)
```

### Enhanced Statistics

```python
stats = registry.get_stats()
print(f"Total agents: {stats['total_agents']}")
print(f"Streaming agents: {stats['capabilities_count']['streaming']}")
print(f"Available input modes: {stats['available_input_modes']}")
print(f"Protocol versions: {stats['protocol_versions']}")
```

### Registry Metadata Access

```python
for agent in registry.get_all():
    print(f"Agent: {agent.name}")
    print(f"Registry ID: {agent.registry_id}")  # Smart property
    print(f"Source: {agent.registry_source}")   # Smart property
```

### Async Support

For high-performance applications:

```python
import asyncio
from a2a_registry import AsyncRegistry

async def main():
    async with AsyncRegistry() as registry:
        agents = await registry.get_all()
        weather_agents = await registry.search("weather")
        stats = await registry.get_stats()
        
        # All sync methods available as async
        filtered = await registry.filter_agents(
            capabilities=["streaming"],
            input_modes=["text/plain"]
        )

asyncio.run(main())
```

## A2A SDK Integration

The registry client seamlessly integrates with the official A2A SDK for a complete **discover → invoke** workflow:

```python
import asyncio
from a2a_registry import Registry, AsyncRegistry

async def main():
    # Step 1: Discover agents using the registry
    # Using AsyncRegistry is preferred in an async context
    async with AsyncRegistry() as registry:
        agents = await registry.search("weather")
        if not agents:
            print("No weather agents found.")
            return
        agent = agents[0]

    # Step 2: Connect using the async method
    client = await agent.async_connect()

    # Step 3: Invoke skills using A2A protocol
    response = await client.message.send(
        skill_id="weather.forecast",
        input={"city": "San Francisco"}
    )
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

### Key Features

- **One-line connection**: `agent.connect()` returns a configured A2A client
- **Automatic configuration**: Agent URL and metadata used automatically
- **Optional dependency**: Only installed when needed (`pip install 'a2a-registry-client[a2a]'`)
- **Full A2A SDK access**: Use all official SDK features (streaming, tasks, etc.)

### Advanced Integration Examples

```python
# Filter before connecting
streaming_agents = registry.find_by_capability("streaming")
agent = streaming_agents[0]
client = agent.connect()

# Use streaming responses
async for chunk in client.message.stream(
    skill_id="chat",
    input={"message": "Hello!"}
):
    print(chunk)

# Pass custom configuration
client = agent.connect(
    auth={"type": "bearer", "token": "..."},
    timeout=30
)
```

### Error Handling

```python
try:
    client = agent.connect()
except ImportError:
    print("Install A2A SDK: pip install 'a2a-registry-client[a2a]'")
except ValueError:
    print("Agent doesn't have a URL configured")
```

See [examples/a2a_integration.py](examples/a2a_integration.py) for complete examples.

## Caching

The client automatically caches the registry data for 5 minutes to reduce network requests. You can customize and control caching:

```python
# Custom cache duration (10 minutes)
registry = Registry(cache_duration=600)

# Manual cache control
registry.refresh()      # Force reload from API
registry.clear_cache()  # Clear cache
```

## Contributing

Contributions are welcome! Please see the main [A2A Registry repository](https://github.com/prassanna-ravishankar/a2a-registry) for contribution guidelines.

## License

MIT License - see LICENSE file for details.