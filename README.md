# A2A Registry

> A community-driven, open-source directory of AI agents using the A2A Protocol

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Website](https://img.shields.io/badge/website-a2aregistry.org-blue)](https://www.a2aregistry.org)
[![Python Client](https://img.shields.io/pypi/v/a2a-registry-client)](https://pypi.org/project/a2a-registry-client/)

## Overview

The A2A Registry is the discovery layer for AI agents. We index **live, hosted agents** that implement the [A2A Protocol](https://a2a-protocol.org), making them discoverable by other agents and applications.

**Key principle**: We trust the agent card. If your agent publishes a valid `.well-known/agent.json`, you can register it with a single API call.

## Quick Start

### Register Your Agent

**Option 1: API (Recommended)**

```bash
curl -X POST https://a2aregistry.org/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{"wellKnownURI": "https://your-agent.com/.well-known/agent.json"}'
```

That's it. We fetch your agent card and register it automatically.

**Option 2: GitHub PR**

1. Fork this repository
2. Add your agent JSON to `/agents/your-agent.json`
3. Submit a Pull Request

### Find Agents

**Web UI**: [a2aregistry.org](https://www.a2aregistry.org)

**API**:
```bash
# List all agents
curl https://a2aregistry.org/api/agents

# Filter by skill
curl https://a2aregistry.org/api/agents?skill=weather

# Get stats
curl https://a2aregistry.org/api/stats
```

**Python Client**:
```bash
pip install a2a-registry-client
```

```python
from a2a_registry import Registry

registry = Registry()
agents = registry.get_all()
weather_agents = registry.find_by_skill("weather")
```

## API Reference

Base URL: `https://a2aregistry.org/api`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agents/register` | POST | Register agent by wellKnownURI |
| `/agents` | GET | List agents (with filtering) |
| `/agents` | POST | Register agent (full payload) |
| `/agents/{id}` | GET | Get agent details |
| `/agents/{id}` | DELETE | Remove agent (ownership verified) |
| `/agents/{id}/health` | GET | Get health status |
| `/agents/{id}/uptime` | GET | Get uptime metrics |
| `/stats` | GET | Registry statistics |
| `/health` | GET | API health check |

### Query Parameters (GET /agents)

- `skill` - Filter by skill ID
- `capability` - Filter by A2A capability (streaming, pushNotifications)
- `author` - Filter by author name
- `limit` - Max results (default: 50, max: 100)
- `offset` - Pagination offset

## Agent Card Format

Your `.well-known/agent.json` should follow the [A2A Protocol AgentCard specification](https://a2a-protocol.org/latest/specification/):

```json
{
  "protocolVersion": "0.3.0",
  "name": "WeatherBot",
  "description": "Real-time weather information and forecasts",
  "url": "https://api.weatherbot.com/a2a",
  "version": "1.0.0",
  "provider": {
    "organization": "Weather Services Inc",
    "url": "https://weatherbot.com"
  },
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": false
  },
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["application/json"],
  "skills": [
    {
      "id": "current-weather",
      "name": "Current Weather",
      "description": "Get current weather conditions",
      "tags": ["weather", "forecast"],
      "inputModes": ["text/plain"],
      "outputModes": ["application/json"]
    }
  ]
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    a2aregistry.org                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React)  │  API (FastAPI)  │  Worker (Background) │
│   - Browse agents  │  - CRUD agents  │  - Health checks     │
│   - Search/filter  │  - Registration │  - Uptime tracking   │
│   - Agent details  │  - Statistics   │  - Periodic sync     │
└─────────────────────────────────────────────────────────────┘
                              │
                      ┌───────┴───────┐
                      │  PostgreSQL   │
                      │  (Cloud SQL)  │
                      └───────────────┘
```

**Deployment**: GKE Autopilot with Helm charts (see `/helm/a2aregistry/`)

## Project Structure

```
a2a-registry/
├── agents/           # Agent JSON files (seeded to database)
├── backend/          # FastAPI application
│   ├── app/          # API routes, models, repositories
│   ├── migrations/   # Database schema
│   └── worker.py     # Health check background service
├── website/          # React frontend
├── client-python/    # Python SDK (published to PyPI)
├── helm/             # Kubernetes deployment charts
└── .github/          # CI/CD workflows
```

## Development

### Local Setup

```bash
# Start all services
docker-compose up

# API available at http://localhost:8000
# Frontend at http://localhost:5173
```

### Backend Development

```bash
cd backend
uv sync
uv run python run.py
```

### Frontend Development

```bash
cd website
npm install
npm run dev
```

## Contributing

1. **Register your agent** - Use the API or submit a PR
2. **Report issues** - [GitHub Issues](https://github.com/prassanna-ravishankar/a2a-registry/issues)
3. **Improve the code** - PRs welcome for features and fixes

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE)

## Links

- **Website**: [a2aregistry.org](https://www.a2aregistry.org)
- **API Docs**: [a2aregistry.org/api/docs](https://a2aregistry.org/api/docs)
- **A2A Protocol**: [a2a-protocol.org](https://a2a-protocol.org)
- **Python Client**: [PyPI](https://pypi.org/project/a2a-registry-client/)
