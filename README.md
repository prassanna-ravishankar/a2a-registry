# A2A Registry

> A community-driven, open-source directory of AI agents using the A2A Protocol

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Website](https://img.shields.io/badge/website-a2aregistry.org-blue)](https://www.a2aregistry.org)
[![Python Client](https://img.shields.io/pypi/v/a2a-registry-client)](https://pypi.org/project/a2a-registry-client/)

## Overview

The A2A Registry solves the critical problem of agent discovery in the AI ecosystem. Using a "Git as a Database" model, we leverage GitHub for transparent data submission, validation, and hosting. The registry is accessible both to humans via our website and to agents programmatically via a static API endpoint.

## Key Features

- **Open Source**: Fully transparent, community-driven development
- **A2A Protocol Compliant**: Follows the Agent-to-Agent protocol standards
- **Simple Submission**: Submit agents via GitHub Pull Requests
- **Automatic Validation**: CI/CD pipeline validates all submissions
- **Multiple Access Methods**: Web UI, JSON API, and Python client
- **No Backend Required**: Static hosting via GitHub Pages

## Quick Start

### For Agent Developers (Submitting an Agent)

1. Fork this repository
2. Create a new JSON file in `/agents/` directory (e.g., `/agents/my-agent.json`)
3. Follow the [Agent Schema](schemas/agent.schema.json) specification
4. Submit a Pull Request
5. Our CI will validate your submission automatically

Example agent entry:
```json
{
  "name": "WeatherBot",
  "description": "Provides real-time weather information and forecasts for any location",
  "author": "Weather Services Inc",
  "wellKnownURI": "https://weatherbot.example.com/.well-known/agent.json",
  "skills": [
    {
      "id": "current-weather",
      "name": "Current Weather",
      "description": "Get current weather conditions for a location",
      "inputModes": ["text", "application/json"],
      "outputModes": ["text", "application/json"]
    }
  ],
  "version": "1.0.0"
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
pip install a2a-registry-client
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
   - Agent ownership via `.well-known/agent.json` verification
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
1. Conform to the [Agent JSON Schema](schemas/agent.schema.json)
2. Include a valid `wellKnownURI` pointing to `.well-known/agent.json`
3. Match key fields between submission and the well-known endpoint
4. Pass all automated validation checks

## API Documentation

### Registry Endpoint
- **URL**: `https://www.a2aregistry.org/registry.json`
- **Method**: GET
- **Response**: JSON array of all registered agents

### Agent Schema
See [schemas/agent.schema.json](schemas/agent.schema.json) for the complete specification.

## Development

### Prerequisites
- Python 3.8+
- uv (for Python package management)
- Node.js 16+ (for website development)

### Local Setup
```bash
# Clone the repository
git clone https://github.com/a2aregistry/a2a-registry.git
cd a2a-registry

# Set up Python environment with uv
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Run validation locally
python scripts/validate_agent.py agents/example.json

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
- [ ] Basic website

### Phase 2: Usability
- [ ] Python client library
- [ ] Searchable website UI
- [ ] Comprehensive documentation

### Phase 3: Growth
- [ ] 20+ agent submissions
- [ ] Governance model
- [ ] Advanced features (semantic search, health checks)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/a2aregistry/a2a-registry/issues)
- **Discussions**: [GitHub Discussions](https://github.com/a2aregistry/a2a-registry/discussions)
- **Website**: [a2aregistry.org](https://www.a2aregistry.org)

## Acknowledgments

Built with ❤️ by the A2A community, leveraging the [A2A Protocol](https://a2aprotocol.ai/) for agent interoperability.