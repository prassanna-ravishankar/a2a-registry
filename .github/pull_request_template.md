## Description

<!-- Please provide a brief description of your changes -->

## Type of Change

<!-- Please check the relevant option(s) -->

- [ ] 🤖 Adding a new agent to the registry
- [ ] 🔧 Updating an existing agent
- [ ] 📚 Documentation update
- [ ] 🐛 Bug fix
- [ ] ✨ New feature
- [ ] 🔨 Infrastructure/tooling improvement

## Agent Submission Checklist

<!-- If submitting a new agent, please ensure: -->

- [ ] Agent follows the A2A Protocol specification
- [ ] Agent has a valid `.well-known/agent-card.json` or `.well-known/agent.json` endpoint
- [ ] Agent JSON file includes all required fields:
  - [ ] `protocolVersion`, `name`, `description`, `url`, `version`
  - [ ] `capabilities`, `skills`, `defaultInputModes`, `defaultOutputModes`
  - [ ] `author`, `wellKnownURI`
- [ ] Skills have `id`, `name`, `description`, and `tags`
- [ ] Agent is publicly accessible and functional
- [ ] Local validation passes: `uv run python scripts/validate_agent.py agents/your-agent.json`

## Testing

<!-- Please describe how you tested your changes -->

- [ ] I have tested my agent locally
- [ ] I have verified the agent's endpoints are accessible
- [ ] I have run the validation script locally

## Additional Notes

<!-- Any additional information that might be helpful for reviewers -->
