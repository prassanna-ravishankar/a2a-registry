# Contributing to A2A Registry

Thank you for your interest in contributing to the A2A Registry! This document covers how to register your agent and contribute to the project.

## Table of Contents

- [Registering an Agent](#registering-an-agent)
- [Agent Requirements](#agent-requirements)
- [Contributing Code](#contributing-code)
- [Community Guidelines](#community-guidelines)
- [Releasing (Maintainers Only)](#releasing-maintainers-only)

## Registering an Agent

**Important**: The A2A Registry only accepts **live, hosted agents** that are publicly accessible. Your agent must be deployed and operational before registration.

### Prerequisites

1. A deployed AI agent implementing the [A2A Protocol](https://a2a-protocol.org)
2. A publicly accessible `.well-known/agent.json` or `.well-known/agent-card.json` endpoint
3. A live A2A endpoint that responds to requests

### Agent Requirements

#### A2A Protocol Compliance

Your agent must serve a valid Agent Card at:
```
https://your-domain.com/.well-known/agent.json
```
or
```
https://your-domain.com/.well-known/agent-card.json
```

The Agent Card must follow the [A2A Protocol specification](https://a2a-protocol.org/latest/specification/#55-agentcard-object-structure) and include:

- `protocolVersion`: e.g. `"0.3.0"`
- `name`: Display name
- `description`: What your agent does
- `url`: The A2A endpoint URL
- `version`: Your agent's version
- `capabilities`: Object declaring protocol capabilities (streaming, pushNotifications, etc.)
- `skills`: Array of skills (each with id, name, description, tags)
- `defaultInputModes` and `defaultOutputModes`

Example Agent Card:
```json
{
  "protocolVersion": "0.3.0",
  "name": "TranslateBot Pro",
  "description": "Advanced multi-language translation agent",
  "url": "https://api.translatebot.example.com/a2a",
  "version": "2.1.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": false
  },
  "skills": [
    {
      "id": "translate-text",
      "name": "Text Translation",
      "description": "Translate text between any supported languages",
      "tags": ["translation", "language"]
    }
  ],
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["application/json"]
}
```

### How to Register

**Option 1: Web UI (Recommended)**

1. Go to [a2aregistry.org/submit](https://a2aregistry.org/submit)
2. Enter your well-known URI (e.g. `https://your-agent.com/.well-known/agent.json`)
3. Click **REGISTER_AGENT** — the system fetches and validates your agent card automatically
4. Your agent appears in the registry immediately

**Option 2: API**

```bash
curl -X POST https://a2aregistry.org/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{"wellKnownURI": "https://your-agent.com/.well-known/agent.json"}'
```

That's it. We fetch your agent card and register it automatically.

## Contributing Code

We welcome contributions to the registry infrastructure!

### Areas for Contribution

- **Frontend**: Enhanced search, filtering, UI/UX improvements (`/website/`)
- **Backend**: API features, validation improvements (`/backend/`)
- **Client libraries**: Python SDK and potential SDKs for other languages (`/client-python/`)
- **Documentation**: Tutorials, examples, guides
- **Testing**: Unit tests, integration tests

### Project Structure

```
a2a-registry/
├── backend/          # FastAPI application
│   ├── app/          # API routes, models, repositories
│   ├── migrations/   # Database schema
│   └── worker.py     # Health check background service
├── website/          # React frontend
├── client-python/    # Python SDK (published to PyPI)
├── helm/             # Kubernetes deployment charts
└── .github/          # CI/CD workflows
```

### Development Setup

```bash
# Start all services
docker-compose up

# API: http://localhost:8000
# Frontend: http://localhost:5173
```

**Backend only:**
```bash
cd backend
uv sync
uv run python run.py
```

**Frontend only:**
```bash
cd website
npm install
npm run dev
```

### Code Style

- Python: Follow PEP 8, use ruff for formatting
- JavaScript/React: Use Prettier for formatting
- Commit messages: Short, imperative one-liners

### Testing

```bash
# Python tests
cd backend
uv run pytest

# Frontend
cd website
npm test
```

## Community Guidelines

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback

### Communication

- **Issues**: [GitHub Issues](https://github.com/prassanna-ravishankar/a2a-registry/issues)
- **Discussions**: [GitHub Discussions](https://github.com/prassanna-ravishankar/a2a-registry/discussions)

## Releasing (Maintainers Only)

### Python Client Library

The `a2a-registry-client` package is published to PyPI via a tag-based workflow.

```bash
git tag v0.2.0
git push --tags
```

The GitHub Actions workflow extracts the version from the tag and publishes to PyPI automatically.

### Deployment

The registry deploys automatically on push to `main` via `.github/workflows/deploy-backend.yml`:
1. Builds container images (api, worker, frontend)
2. Pushes to GCR
3. Deploys to GKE with Helm

See [DEPLOYMENT.md](DEPLOYMENT.md) for manual deployment instructions.

## Questions?

- Check [GitHub Issues](https://github.com/prassanna-ravishankar/a2a-registry/issues)
- Read the [README](README.md)
- Ask in [GitHub Discussions](https://github.com/prassanna-ravishankar/a2a-registry/discussions)

Thank you for contributing to the A2A Registry!
