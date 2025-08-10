# Contributing to A2A Registry

Thank you for your interest in contributing to the A2A Registry! This document provides guidelines for submitting agents and contributing to the project.

## Table of Contents

- [Submitting an Agent](#submitting-an-agent)
- [Agent Requirements](#agent-requirements)
- [Submission Process](#submission-process)
- [Contributing Code](#contributing-code)
- [Community Guidelines](#community-guidelines)

## Submitting an Agent

### Prerequisites

Before submitting your agent, ensure you have:

1. A working AI agent that follows the A2A Protocol
2. A publicly accessible `.well-known/agent.json` endpoint
3. Clear documentation about your agent's capabilities
4. Tested your agent's functionality

### Agent Requirements

All submitted agents must meet these requirements:

#### 1. A2A Protocol Compliance

Your agent must have a valid A2A Protocol Agent Card accessible at:
```
https://your-domain.com/.well-known/agent.json
```

The Agent Card should follow the A2A Protocol specification and include:
- Basic information (name, description, version)
- Skills array with detailed descriptions
- Supported capabilities
- Authentication requirements (if any)

#### 2. JSON Schema Compliance

Your submission file must validate against our [Agent Schema](schemas/agent.schema.json). Required fields:

- `name`: Your agent's display name (max 100 characters)
- `description`: Clear description of what your agent does (10-500 characters)
- `author`: Your name or organization
- `wellKnownURI`: Full URL to your `.well-known/agent.json` endpoint
- `skills`: Array of skills with `id`, `name`, and `description` for each

#### 3. Ownership Verification

The `name` and `description` in your submission must match those in your `.well-known/agent.json` endpoint to verify ownership.

## Submission Process

### Step 1: Fork the Repository

Fork the [A2A Registry repository](https://github.com/a2aregistry/a2a-registry) to your GitHub account.

### Step 2: Create Your Agent File

Create a new JSON file in the `/agents/` directory. Name it descriptively:
```
agents/your-agent-name.json
```

Example agent file:
```json
{
  "name": "TranslateBot Pro",
  "description": "Advanced multi-language translation agent supporting 100+ languages with context awareness",
  "author": "Language Services Inc",
  "wellKnownURI": "https://translatebot.example.com/.well-known/agent.json",
  "skills": [
    {
      "id": "translate-text",
      "name": "Text Translation",
      "description": "Translate text between any supported languages",
      "inputModes": ["text/plain", "application/json"],
      "outputModes": ["text/plain", "application/json"],
      "tags": ["translation", "language", "text"]
    },
    {
      "id": "detect-language",
      "name": "Language Detection",
      "description": "Automatically detect the language of input text",
      "inputModes": ["text/plain"],
      "outputModes": ["application/json"]
    }
  ],
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "version": "2.1.0",
  "homepage": "https://translatebot.example.com",
  "documentation": "https://docs.translatebot.example.com/api",
  "tags": ["translation", "language", "nlp"]
}
```

### Step 3: Validate Locally (Optional)

Test your submission locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Validate your agent file
python scripts/validate_agent.py agents/your-agent-name.json
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
- Python users can discover it using the `a2a-registry-client` package

## Contributing Code

We welcome contributions to improve the registry infrastructure!

### Areas for Contribution

- **Website improvements**: Enhanced search, filtering, UI/UX improvements
- **Validation enhancements**: Additional checks, better error messages
- **Client libraries**: SDKs for other languages (JavaScript, Go, Rust, etc.)
- **Documentation**: Tutorials, examples, guides
- **Testing**: Unit tests, integration tests, CI improvements

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/a2aregistry/a2a-registry.git
   cd a2a-registry
   ```

2. Set up Python environment with uv:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

3. For client development:
   ```bash
   cd client-python
   uv pip install -e ".[dev]"
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

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/a2aregistry/a2a-registry/issues)
- **Discussions**: General questions and discussions in [GitHub Discussions](https://github.com/a2aregistry/a2a-registry/discussions)
- **Pull Requests**: Submit code changes with clear descriptions

### Review Process

1. All submissions are automatically validated by GitHub Actions
2. Maintainers review for:
   - Compliance with requirements
   - Appropriate content
   - No duplicate agents
3. Feedback provided via PR comments
4. Approved PRs are merged promptly

## Questions?

If you have questions:
1. Check existing [issues](https://github.com/a2aregistry/a2a-registry/issues)
2. Read the [documentation](README.md)
3. Ask in [discussions](https://github.com/a2aregistry/a2a-registry/discussions)

Thank you for contributing to the A2A Registry! Together we're building a comprehensive, open directory of AI agents.