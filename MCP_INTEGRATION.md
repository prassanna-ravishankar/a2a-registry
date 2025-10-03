# MCP Server Integration

The A2A Registry provides a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that enables AI assistants like Claude to directly discover and query agents from the registry.

[![PyPI](https://img.shields.io/pypi/v/a2a-registry-client)](https://pypi.org/project/a2a-registry-client/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io/)

## What is MCP?

The Model Context Protocol is an open standard that allows AI assistants to securely connect to external data sources and tools. By integrating the A2A Registry MCP server, AI assistants can:

- **Discover agents** by searching across names, descriptions, and skills
- **Filter agents** by capabilities, skills, authors, or input/output modes
- **Query metadata** to understand agent capabilities and requirements
- **Access real-time data** directly from the live registry

## Quick Start

The fastest way to use the MCP server is with `uvx` (no installation required):

```bash
uvx a2a-registry-client
```

## Installation

### Using uvx (Recommended)

[uvx](https://docs.astral.sh/uv/) allows you to run the MCP server without installing it globally:

```bash
# Run directly with uvx
uvx a2a-registry-client
```

### Using pip

For persistent installation:

```bash
pip install a2a-registry-client
a2a-registry-client
```

## Configuration

Choose your tool below for specific setup instructions:

<details>
<summary><strong>Claude Desktop</strong></summary>

The most popular way to use the A2A Registry MCP server.

**Configuration File Location:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}
```

**After configuration:**
1. Save the file
2. Restart Claude Desktop completely
3. Look for the 🔌 icon in Claude to verify MCP servers are loaded

**Alternative (if you have it installed):**
```json
{
  "mcpServers": {
    "a2a-registry": {
      "command": "a2a-registry-client"
    }
  }
}
```
</details>

<details>
<summary><strong>Cline (VS Code Extension)</strong></summary>

Cline is a popular AI coding assistant for VS Code with MCP support.

**Setup:**

1. Install the Cline extension from VS Code marketplace
2. Open VS Code Settings (`Cmd/Ctrl + ,`)
3. Search for "Cline: MCP Settings"
4. Click "Edit in settings.json"
5. Add the configuration:

```json
{
  "cline.mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}
```

6. Restart VS Code or reload the Cline extension

**Verify:** Cline should now be able to query the A2A Registry when you ask about agents.
</details>

<details>
<summary><strong>Zed Editor</strong></summary>

Zed is a high-performance code editor with built-in MCP support.

**Configuration File Location:**
- `~/.config/zed/settings.json`

**Configuration:**
```json
{
  "context_servers": {
    "a2a-registry": {
      "command": {
        "path": "uvx",
        "args": ["a2a-registry-client"]
      }
    }
  }
}
```

**After configuration:**
1. Save the settings file
2. Restart Zed
3. The MCP server should appear in Zed's context menu

**Documentation:** [Zed MCP Documentation](https://zed.dev/docs/assistant/model-context-protocol)
</details>

<details>
<summary><strong>Continue (VS Code Extension)</strong></summary>

Continue is an open-source AI code assistant with MCP integration.

**Setup:**

1. Install the Continue extension from VS Code marketplace
2. Open Continue settings (click the gear icon in Continue panel)
3. Navigate to the MCP section
4. Add the server configuration:

```json
{
  "mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}
```

5. Restart VS Code

**Verify:** Use Continue's chat to ask about agents in the registry.

**Documentation:** [Continue MCP Setup](https://docs.continue.dev/features/model-context-protocol)
</details>

<details>
<summary><strong>Cursor</strong></summary>

Cursor is an AI-first code editor with MCP support.

**Setup:**

1. Open Cursor Settings (`Cmd/Ctrl + ,`)
2. Search for "MCP" or navigate to AI/MCP settings
3. Add the server configuration:

```json
{
  "mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}
```

4. Restart Cursor

**Note:** MCP support in Cursor may be in beta. Check Cursor's documentation for the latest setup instructions.
</details>

<details>
<summary><strong>Smithery (One-Click Install)</strong></summary>

Smithery provides one-click installation for MCP servers.

**Install:**

[![Install on Smithery](https://smithery.ai/badge/@a2a-registry/client)](https://smithery.ai/server/@a2a-registry/client)

Click the badge above or visit: https://smithery.ai/server/a2a-registry-client

**What Smithery does:**
- Automatically configures the MCP server in your chosen tool
- Manages updates and dependencies
- Simplifies installation across multiple IDEs

*Note: Package may need to be published to Smithery first*
</details>

<details>
<summary><strong>Generic MCP Client / Custom Integration</strong></summary>

For custom MCP client implementations or other tools not listed above.

**Command:**
```bash
uvx a2a-registry-client
```

**Or if installed via pip:**
```bash
a2a-registry-client
```

**Configuration Pattern (JSON):**
```json
{
  "mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}
```

**Technical Details:**
- **Protocol**: [MCP Specification](https://spec.modelcontextprotocol.io/)
- **Transport**: stdio (standard input/output)
- **Server name**: `A2A Registry`
- **Language**: Python 3.10+

**Testing:**
Use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to test the server:

```bash
npx @modelcontextprotocol/inspector uvx a2a-registry-client
```
</details>

## Available Tools

Once configured, AI assistants can use the following tools:

### Discovery & Search

- **`search_agents(query: str)`**
  - Full-text search across agent names, descriptions, and skills
  - Example: `search_agents("weather forecast")`

- **`list_all_agents()`**
  - Retrieve all agents in the registry
  - Returns complete agent metadata

- **`get_agent(agent_id: str)`**
  - Get detailed information about a specific agent
  - Example: `get_agent("weather-bot")`

### Filtering

- **`find_by_capability(capability: str)`**
  - Find agents with specific A2A capabilities
  - Examples: `streaming`, `pushNotifications`, `stateTransitionHistory`

- **`find_by_skill(skill_id: str)`**
  - Find agents offering a particular skill
  - Example: `find_by_skill("weather-forecast")`

- **`find_by_author(author: str)`**
  - Find all agents created by a specific author
  - Example: `find_by_author("Weather Services Inc")`

- **`find_by_input_mode(input_mode: str)`**
  - Find agents supporting a specific input MIME type
  - Examples: `text/plain`, `image/jpeg`, `audio/mpeg`

- **`find_by_output_mode(output_mode: str)`**
  - Find agents supporting a specific output MIME type
  - Examples: `application/json`, `text/plain`, `image/png`

- **`filter_agents(skills, capabilities, input_modes, output_modes, authors, tags, protocol_version)`**
  - Advanced multi-criteria filtering (AND logic)
  - All parameters are optional lists/strings

### Metadata

- **`get_registry_stats()`**
  - Get registry statistics (total agents, capabilities, skills, etc.)

- **`list_capabilities()`**
  - List all A2A protocol capabilities available in the registry

- **`refresh_registry()`**
  - Force refresh the registry cache to get latest data

## Example Usage

Once configured in Claude Desktop or other MCP clients, you can ask:

```
"Find agents that support streaming"
"Search for chess-playing agents"
"Show me all agents by Weather Services Inc"
"Which agents support JSON output?"
"What are the registry statistics?"
"Find agents with weather-forecast skill"
```

The AI assistant will automatically call the appropriate MCP tools and present the results.

## Data Freshness

The MCP server caches registry data for 5 minutes to optimize performance. You can:
- Wait for automatic cache refresh (every 5 minutes)
- Use the `refresh_registry()` tool to force an immediate refresh
- Restart the MCP server for a clean cache

## Development

### Testing Locally

```bash
# Clone the repository
git clone https://github.com/prassanna-ravishankar/a2a-registry.git
cd a2a-registry/client-python

# Run with uv
uv run a2a-registry-client

# Or install in editable mode
pip install -e .
a2a-registry-client
```

### Debugging

To test the MCP server manually:

```bash
# Start the server
uvx a2a-registry-client

# The server will wait for MCP protocol messages on stdin
# You can test using the MCP Inspector or custom MCP client
```

## Requirements

- Python 3.10 or higher
- `uvx` (part of the `uv` package) or `pip` for installation

## Troubleshooting

### Server not starting

- Ensure Python 3.10+ is installed: `python --version`
- Try installing directly: `pip install a2a-registry-client`
- Check for conflicting Python environments

### Server not appearing in Claude Desktop

- Verify the config file location and syntax
- Restart Claude Desktop completely
- Check Claude Desktop logs for errors

### No results from queries

- Use `refresh_registry()` to update the cache
- Verify internet connectivity (server needs to fetch from a2aregistry.org)
- Check the [registry status](https://www.a2aregistry.org/registry.json)

## Learn More

- [A2A Protocol Specification](https://a2a-protocol.org/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Python Client Documentation](https://github.com/prassanna-ravishankar/a2a-registry/tree/main/client-python)
- [Submit an Agent](https://github.com/prassanna-ravishankar/a2a-registry#quick-start)

## Support

- **Issues**: [GitHub Issues](https://github.com/prassanna-ravishankar/a2a-registry/issues)
- **Discussions**: [GitHub Discussions](https://github.com/prassanna-ravishankar/a2a-registry/discussions)
- **Website**: [a2aregistry.org](https://www.a2aregistry.org)
