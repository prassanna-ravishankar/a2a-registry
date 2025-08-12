# A2A Registry Python Client

Official Python client library for the A2A Registry - a community-driven directory of AI agents.

## Installation

```bash
pip install a2a-registry-client
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

## Caching

The client automatically caches the registry data for 5 minutes to reduce network requests. You can force a refresh:

```python
registry = Registry()
registry.refresh()  # Force reload from the API
```

## Contributing

Contributions are welcome! Please see the main [A2A Registry repository](https://github.com/a2aregistry/a2a-registry) for contribution guidelines.

## License

MIT License - see LICENSE file for details.