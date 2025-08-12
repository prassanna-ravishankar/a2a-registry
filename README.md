# A2A Registry

> A community-driven, open-source directory of AI agents using the A2A Protocol

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Website](https://img.shields.io/badge/website-a2aregistry.org-blue)](https://www.a2aregistry.org)
[![Python Client](https://img.shields.io/pypi/v/a2a-registry-client)](https://pypi.org/project/a2a-registry-client/)

## Overview

The A2A Registry solves the critical problem of agent discovery in the AI ecosystem. Using a "Git as a Database" model, we leverage GitHub for transparent data submission, validation, and hosting. The registry is accessible both to humans via our website and to agents programmatically via a static API endpoint.

## Key Features

- **Open Source**: Fully transparent, community-driven development
- **A2A Protocol Compliant**: Uses official A2A Protocol AgentCard specification
- **Simple Submission**: Submit agents via GitHub Pull Requests
- **Automatic Validation**: CI/CD pipeline validates both A2A compliance and registry requirements
- **Multiple Access Methods**: Web UI, JSON API, and Python client
- **No Backend Required**: Static hosting via GitHub Pages

## Quick Start

### For Agent Developers (Submitting an Agent)

1. Fork this repository
2. Create a new JSON file in `/agents/` directory (e.g., `/agents/my-agent.json`)
3. Follow the [Official A2A AgentCard specification](https://a2a-protocol.org/latest/specification/#55-agentcard-object-structure)
4. Include required registry fields: `author` and `wellKnownURI`
5. Submit a Pull Request
6. Our CI will validate your submission for both A2A compliance and registry requirements

Example agent entry (A2A Protocol compliant):
```json
{
  "protocolVersion": "0.3.0",
  "name": "WeatherBot",
  "description": "Provides real-time weather information and forecasts",
  "url": "https://api.weatherbot.example.com/a2a",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "current-weather",
      "name": "Current Weather",
      "description": "Get current weather conditions",
      "tags": ["weather", "current"],
      "inputModes": ["text/plain", "application/json"],
      "outputModes": ["application/json"]
    }
  ],
  "defaultInputModes": ["text/plain", "application/json"],
  "defaultOutputModes": ["application/json"],
  "author": "Weather Services Inc",
  "wellKnownURI": "https://weatherbot.example.com/.well-known/agent.json"
}
```

### For Agent Consumers (Finding Agents)

#### Via Web Browser
Visit [https://www.a2aregistry.org](https://www.a2aregistry.org) to browse and search the registry.

#### Via API
```bash
curl https://www.a2aregistry.org/registry.json
```

#### Via Python Client
```bash
uv pip install a2a-registry-client
# Or using pip: pip install a2a-registry-client
```

```python
from a2a_registry import Registry

registry = Registry()
agents = registry.get_all()

# Find agents with specific skills
weather_agents = registry.find_by_skill("weather-forecast")
```

## Project Structure

```
a2a-registry/
├── agents/              # Agent JSON files (the "database")
├── docs/                # Website static files
├── client-python/       # Python client library source
├── .github/workflows/   # GitHub Actions for automation
├── schemas/             # JSON Schema definitions
└── scripts/             # Utility scripts
```

## How It Works

1. **Submission**: Developers submit agent definitions as JSON files via Pull Requests
2. **Validation**: GitHub Actions automatically validate:
   - JSON schema compliance
   - Agent ownership via `.well-known/agent.json` or `.well-known/agent-card.json` verification
3. **Publishing**: On merge, the system:
   - Consolidates all agents into `registry.json`
   - Deploys to GitHub Pages
   - Updates the Python client if needed

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Submitting agents
- Improving documentation
- Enhancing the validation pipeline
- Developing new features

## Validation Requirements

All agent submissions must:
1. Conform to the [Official A2A Protocol AgentCard specification](schemas/a2a-official.schema.json)
2. Include all required A2A fields: `protocolVersion`, `name`, `description`, `url`, `version`, `capabilities`, `skills`, `defaultInputModes`, `defaultOutputModes`
3. Include registry-specific fields: `author` and `wellKnownURI`
4. Skills must have: `id`, `name`, `description`, and `tags`
5. Match key fields between submission and the `.well-known/agent.json` or `.well-known/agent-card.json` endpoint
6. Pass all automated validation checks

## API Documentation

### Registry Endpoint
- **URL**: `https://www.a2aregistry.org/registry.json`
- **Method**: GET
- **Response**: JSON array of all registered agents

### Agent Schema
- **A2A Protocol Schema**: [schemas/a2a-official.schema.json](schemas/a2a-official.schema.json)
- **Registry Extensions**: [schemas/registry-agent.schema.json](schemas/registry-agent.schema.json)
- **Official A2A Docs**: [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)

## Development

### Prerequisites
- Python 3.10+
- uv (for Python package management)

### Local Setup
```bash
# Clone the repository
git clone https://github.com/prassanna-ravishankar/a2a-registry.git
cd a2a-registry

# Set up Python environment with uv
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Note: uv provides automatic dependency caching for faster installs
# For users who prefer pip: pip install -r requirements.txt

# Run validation locally
python scripts/validate_agent.py agents/example-weather-bot.json

# Generate registry.json
python scripts/generate_registry.py agents/ > docs/registry.json

# Serve website locally
cd docs && python -m http.server 8000
```

## Roadmap

### Phase 1: MVP ✅
- [x] Repository structure
- [x] Agent JSON Schema
- [ ] GitHub Actions validation
- [x] Basic website

### Phase 2: Usability
- [x] Python client library
- [ ] Searchable website UI
- [ ] Comprehensive documentation

### Phase 3: Growth
- [ ] 20+ agent submissions
- [ ] Governance model
- [ ] Advanced features (semantic search, health checks)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/prassanna-ravishankar/a2a-registry/issues)
- **Discussions**: [GitHub Discussions](https://github.com/prassanna-ravishankar/a2a-registry/discussions)
- **Website**: [a2aregistry.org](https://www.a2aregistry.org)

## Acknowledgments

Built with ❤️ by the A2A community, leveraging the [A2A Protocol](https://a2a-protocol.org/) for agent interoperability.