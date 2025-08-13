# Contributing to A2A Registry

Thank you for your interest in contributing to the A2A Registry! This document provides guidelines for submitting agents and contributing to the project.

## Table of Contents

- [Submitting an Agent](#submitting-an-agent)
- [Agent Requirements](#agent-requirements)
- [Submission Process](#submission-process)
- [Contributing Code](#contributing-code)
- [Community Guidelines](#community-guidelines)
- [Releasing (Maintainers Only)](#releasing-maintainers-only)

## Submitting an Agent

### Prerequisites

Before submitting your agent, ensure you have:

1. A working AI agent that follows the A2A Protocol
2. A publicly accessible `.well-known/agent.json` or `.well-known/agent-card.json` endpoint
3. Clear documentation about your agent's capabilities
4. Tested your agent's functionality

### Agent Requirements

All submitted agents must meet these requirements:

#### 1. A2A Protocol Compliance

Your agent must have a valid A2A Protocol Agent Card accessible at:
```
https://your-domain.com/.well-known/agent.json or https://your-domain.com/.well-known/agent-card.json
```

**Note**: `.well-known/agent-card.json` is preferred per the A2A Protocol specification.

The Agent Card must follow the [Official A2A Protocol specification](https://a2a-protocol.org/latest/specification/#55-agentcard-object-structure) and include:
- **Required A2A fields**: protocolVersion, name, description, url, version, capabilities, skills, defaultInputModes, defaultOutputModes
- **Skills structure**: Each skill must have id, name, description, and tags
- **Capabilities object**: Declare support for streaming, pushNotifications, etc.
- **Provider information** (optional but recommended)

#### 2. JSON Schema Compliance

Your submission file must validate against both:
- [Official A2A Protocol AgentCard schema](schemas/a2a-official.schema.json)
- [Registry-specific requirements](schemas/registry-agent.schema.json)

Required A2A Protocol fields:
- `protocolVersion`: A2A protocol version (e.g., "0.3.0")
- `name`: Your agent's display name
- `description`: Clear description of what your agent does
- `url`: The A2A endpoint URL for your agent
- `version`: Your agent's version
- `capabilities`: Object declaring protocol capabilities
- `skills`: Array of skills (each with id, name, description, tags)
- `defaultInputModes`: Default input MIME types
- `defaultOutputModes`: Default output MIME types

Required registry fields:
- `author`: Your name or organization
- `wellKnownURI`: Full URL to your `.well-known/agent.json` or `.well-known/agent-card.json` endpoint

#### 3. Ownership Verification

The `name` and `description` in your submission must match those in your `.well-known/agent.json` or `.well-known/agent-card.json` endpoint to verify ownership.

## Submission Process

### Step 1: Fork the Repository

Fork the [A2A Registry repository](https://github.com/prassanna-ravishankar/a2a-registry) to your GitHub account.

### Step 2: Create Your Agent File

Create a new JSON file in the `/agents/` directory. Name it descriptively:
```
agents/your-agent-name.json
```

Example agent file (A2A Protocol compliant):
```json
{
  "protocolVersion": "0.3.0",
  "name": "TranslateBot Pro",
  "description": "Advanced multi-language translation agent supporting 100+ languages",
  "url": "https://api.translatebot.example.com/a2a",
  "version": "2.1.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "translate-text",
      "name": "Text Translation",
      "description": "Translate text between any supported languages",
      "tags": ["translation", "language", "text"],
      "inputModes": ["text/plain", "application/json"],
      "outputModes": ["text/plain", "application/json"],
      "examples": ["Translate 'Hello' to Spanish", "Convert this text to French"]
    },
    {
      "id": "detect-language",
      "name": "Language Detection",
      "description": "Automatically detect the language of input text",
      "tags": ["detection", "language", "analysis"],
      "inputModes": ["text/plain"],
      "outputModes": ["application/json"],
      "examples": ["What language is 'Bonjour'?"]
    }
  ],
  "defaultInputModes": ["text/plain", "application/json"],
  "defaultOutputModes": ["application/json"],
  "provider": {
    "organization": "Language Services Inc",
    "url": "https://languageservices.example.com"
  },
  "documentationUrl": "https://docs.translatebot.example.com/api",
  "author": "Language Services Inc",
  "wellKnownURI": "https://translatebot.example.com/.well-known/agent.json",
  "homepage": "https://translatebot.example.com",
  "registryTags": ["translation", "language", "nlp"]
}
```

### Step 3: Validate Locally (Optional)

Test your submission locally:

```bash
# Validate your agent file (checks both A2A compliance and registry requirements)
# Note: uv run automatically handles environment setup and dependencies
uv run python scripts/validate_agent.py agents/your-agent-name.json
```

### Step 4: Submit Pull Request

1. Commit your changes:
   ```bash
   git add agents/your-agent-name.json
   git commit -m "Add TranslateBot Pro agent"
   ```

2. Push to your fork:
   ```bash
   git push origin main
   ```

3. Create a Pull Request to the main repository

4. Wait for automatic validation (GitHub Actions will validate your submission)

5. Address any feedback from maintainers

### Step 5: Post-Merge

Once merged:
- Your agent will appear on [a2aregistry.org](https://www.a2aregistry.org) within minutes
- It will be available via the API at `https://www.a2aregistry.org/registry.json`
- Python users can discover it using the `a2aregistry` package

## Contributing Code

We welcome contributions to improve the registry infrastructure!

### Areas for Contribution

- **Website improvements**: Enhanced search, filtering, UI/UX improvements
- **Validation enhancements**: Additional checks, better error messages
- **Client libraries**: SDKs for other languages (JavaScript, Go, Rust, etc.)
- **Documentation**: Tutorials, examples, guides
- **Testing**: Unit tests, integration tests, CI improvements

### Project Structure

This repository contains two separate Python packages:

1. **Root package (`a2a-registry`)**: Contains validation scripts and registry generation tools
   - Configuration: `/pyproject.toml`
   - Includes: `scripts/validate_agent.py`, `scripts/generate_registry.py`
   - Dependencies: jsonschema (for validation), requests

2. **Client package (`a2aregistry`)**: Python client library for consuming the registry
   - Configuration: `/client-python/pyproject.toml`
   - Published to PyPI separately
   - Dependencies: requests, pydantic (for data models)

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/prassanna-ravishankar/a2a-registry.git
   cd a2a-registry
   ```

2. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. No explicit setup needed! Just use `uv run` to execute commands:
   ```bash
   # For root scripts
   uv run python scripts/validate_agent.py agents/example-weather-bot.json
   
   # For client development
   cd client-python
   uv run pytest tests/
   ```

### Code Style

- Python: Follow PEP 8, use Black for formatting
- JavaScript: Use Prettier for formatting
- Commit messages: Use conventional commits format

### Testing

Run tests before submitting:

```bash
# Python tests
pytest

# Type checking
uvx ty check

# Validate all agents
for file in agents/*.json; do
    python scripts/validate_agent.py "$file"
done
```

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect different perspectives and experiences

### Communication

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/prassanna-ravishankar/a2a-registry/issues)
- **Discussions**: General questions and discussions in [GitHub Discussions](https://github.com/prassanna-ravishankar/a2a-registry/discussions)
- **Pull Requests**: Submit code changes with clear descriptions

### Review Process

1. All submissions are automatically validated by GitHub Actions
2. Maintainers review for:
   - Compliance with requirements
   - Appropriate content
   - No duplicate agents
3. Feedback provided via PR comments
4. Approved PRs are merged promptly

## Releasing (Maintainers Only)

### Python Client Library

The Python client library (`a2aregistry`) is published to PyPI using a tag-based workflow. The version is automatically extracted from the git tag.

#### Prerequisites

1. Ensure you have a PyPI API token set as the `PYPI_API_TOKEN` secret in GitHub
2. Make sure all tests pass and the code is ready for release

#### Release Steps

1. **Create and push a version tag**:
   ```bash
   # Format: v<version>
   git tag v0.2.0
   git push --tags
   ```

2. **Monitor the workflow**:
   - Go to Actions tab in GitHub
   - Watch the "Publish Registry" workflow
   - The version will be automatically extracted from the tag
   - The client will be built and published to PyPI

#### Version Tag Format

- Tags must follow semantic versioning with a `v` prefix
- Examples: `v0.1.0`, `v1.0.0`, `v2.0.0-beta.1`
- The version in `pyproject.toml` will be automatically updated to match the tag (without the `v` prefix)

### Registry Updates

The registry (GitHub Pages site) is automatically updated on every push to `main` that modifies:
- Agent files (`agents/**.json`)
- Documentation (`docs/**`)
- Registry generation script (`scripts/generate_registry.py`)

No manual intervention is needed for registry updates.

## Questions?

If you have questions:
1. Check existing [issues](https://github.com/prassanna-ravishankar/a2a-registry/issues)
2. Read the [documentation](README.md)
3. Ask in [discussions](https://github.com/prassanna-ravishankar/a2a-registry/discussions)

Thank you for contributing to the A2A Registry! Together we're building a comprehensive, open directory of AI agents.