# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A2A Registry is a community-driven, open-source directory of AI agents using a "Git as a Database" model. The registry leverages GitHub for data submission, validation, and hosting, with public access via www.a2aregistry.org and programmatic access through a static API and Python client.

## Development Setup

### Python Environment (using uv)
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
uv pip install -r requirements.txt

# For client library development
cd client-python
uv pip install -e ".[dev]"
```

## Common Development Commands

### GitHub Actions Testing
```bash
# Test GitHub Actions locally (requires act)
act -j validate-pr
act -j publish
```

### Python Client Development
```bash
# Run tests for the Python client
cd client-python
pytest tests/

# Build the package
python -m build

# Check package before publishing
twine check dist/*
```

### Website Development
```bash
# Serve the website locally
cd docs
python -m http.server 8000
# Visit http://localhost:8000
```

### Agent Registry Operations
```bash
# Validate a single agent file
python scripts/validate_agent.py agents/example-agent.json

# Generate registry.json from all agent files
python scripts/generate_registry.py agents/ > docs/registry.json
```

## Architecture & Key Components

### Repository Structure
- `/agents/` - Flat directory containing individual agent JSON files (the "database")
- `/docs/` - Static website files served via GitHub Pages at www.a2aregistry.org
- `/client-python/` - Python client library source (published as `a2a-registry-client`)
- `/.github/workflows/` - GitHub Actions for automation:
  - `validate-pr.yml` - Validates agent submissions on PRs
  - `publish.yml` - Generates registry.json and deploys to GitHub Pages

### Data Flow
1. **Agent Submission**: Developer creates PR with new JSON file in `/agents/`
2. **Validation**: GitHub Action validates JSON schema and verifies ownership via `/.well-known/agent-card.json`
3. **Publishing**: On merge, GitHub Action consolidates all agents into `registry.json` and deploys
4. **Consumption**: Users access via website, API endpoint, or Python client

### Agent JSON Schema
Required fields for each agent:
- `name`: Display name
- `description`: Purpose explanation
- `author`: Creator name/handle
- `wellKnownURI`: Validation endpoint
- `capabilities`: Array of task strings

### Key Endpoints
- Website: `https://www.a2aregistry.org`
- API: `https://www.a2aregistry.org/registry.json`
- PyPI: `pip install a2a-registry-client`

## Development Phases

### Phase 1 (MVP) - Current Focus
- Repository setup and structure
- Agent JSON Schema definition
- GitHub Actions for validation and publishing
- Basic placeholder website

### Phase 2 (Usability)
- Python client library
- Searchable website UI
- Documentation (README, CONTRIBUTING)

### Phase 3 (Growth)
- Community outreach
- Governance model
- Advanced features (semantic search, health checks)