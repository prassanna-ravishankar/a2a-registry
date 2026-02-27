# A2A Registry

> A community-driven, open-source directory of AI agents using the A2A Protocol

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Website](https://img.shields.io/badge/website-a2aregistry.org-blue)](https://www.a2aregistry.org)
[![Python Client](https://img.shields.io/pypi/v/a2a-registry-client)](https://pypi.org/project/a2a-registry-client/)

## Overview

The A2A Registry is the discovery layer for AI agents. We index **live, hosted agents** that implement the [A2A Protocol](https://a2a-protocol.org), making them discoverable by other agents and applications.

**Key principle**: We trust the agent card. If your agent publishes a valid `.well-known/agent.json`, you can register it with a single API call.

## Register Your Agent

Make sure your agent publishes a valid agent card at `https://your-agent.com/.well-known/agent.json`, then:

```bash
curl -X POST https://a2aregistry.org/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{"wellKnownURI": "https://your-agent.com/.well-known/agent.json"}'
```

That's it. We fetch your agent card and register it automatically. The worker checks your agent's health every 30 minutes and updates conformance status.

## Find Agents

**Web UI**: [a2aregistry.org](https://www.a2aregistry.org)

**API**:
```bash
# List standard (A2A-conformant) agents
curl https://a2aregistry.org/api/agents?conformance=standard

# Search by keyword
curl https://a2aregistry.org/api/agents?search=translation

# Filter by skill tag
curl https://a2aregistry.org/api/agents?skill=weather

# Get stats
curl https://a2aregistry.org/api/stats
```

**Python Client**:
```bash
pip install a2a-registry-client
```

```python
from a2a_registry import APIRegistry

registry = APIRegistry()
agents = registry.get_all()
results = registry.search("weather")
```

**MCP Server** (for AI assistants):
```json
{
  "mcpServers": {
    "a2a-registry": {
      "url": "https://a2aregistry.org/mcp/"
    }
  }
}
```

## Agent Card Format

Your `.well-known/agent.json` must follow the [A2A Protocol AgentCard specification](https://a2a-protocol.org/latest/specification/):

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

## API Reference

Base URL: `https://a2aregistry.org/api`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agents/register` | POST | Register agent by wellKnownURI |
| `/agents` | GET | List/search agents |
| `/agents/{id}` | GET | Get agent details |
| `/agents/{id}` | PUT | Re-fetch and update agent from wellKnownURI |
| `/agents/{id}` | DELETE | Remove agent (ownership verified) |
| `/agents/{id}/health` | GET | Get health status |
| `/agents/{id}/uptime` | GET | Get uptime metrics |
| `/stats` | GET | Registry statistics |

### Query Parameters (GET /agents)

| Parameter | Description |
|-----------|-------------|
| `search` | Full-text search across name, description, author |
| `skill` | Filter by skill tag |
| `capability` | Filter by A2A capability (streaming, pushNotifications) |
| `author` | Filter by author name |
| `conformance` | `standard` (A2A spec compliant) or `non-standard` |
| `limit` | Max results (default: 50, max: 100) |
| `offset` | Pagination offset |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    a2aregistry.org                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React)  │  API (FastAPI)  │  Worker (Background) │
│   - Browse agents  │  - CRUD agents  │  - Health checks     │
│   - Search/filter  │  - Registration │  - Uptime tracking   │
│   - Agent details  │  - MCP server   │  - Conformance check │
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
├── backend/          # FastAPI application + MCP server
│   ├── app/          # API routes, models, repositories, MCP
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
docker-compose up
# API: http://localhost:8000
# Frontend: http://localhost:5173
```

### Backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd website
npm install && npm run dev
```

## Contributing

- **Register your agent** — use the API above
- **Report issues** — [GitHub Issues](https://github.com/prassanna-ravishankar/a2a-registry/issues)
- **Improve the code** — PRs welcome for backend, frontend, and infra

## Links

- **Website**: [a2aregistry.org](https://www.a2aregistry.org)
- **API Docs**: [a2aregistry.org/api/docs](https://a2aregistry.org/api/docs)
- **MCP Server**: [a2aregistry.org/mcp/](https://a2aregistry.org/mcp/)
- **A2A Protocol**: [a2a-protocol.org](https://a2a-protocol.org)
- **Python Client**: [PyPI](https://pypi.org/project/a2a-registry-client/)

## License

MIT
