# A2A Registry – TODO

A concise, actionable checklist to fix identified inconsistencies and improve the registry.
Ordered by priority and logical workflow.

## 1. Links and URL Corrections (Foundation)
- [x] Update all repository links to correct URL
  - [x] Change github.com/a2aregistry/a2a-registry to github.com/prassanna-ravishankar/a2a-registry
  - [x] Update in README.md
  - [x] Update in CONTRIBUTING.md  
  - [x] Update in CLAUDE.md
  - [x] Update in client-python/README.md
  - [x] Update in client-python/pyproject.toml
  - [x] Update in docs/index.html (nav links, submit agent links, footer)
- [x] Website URLs are correct with www.a2aregistry.org ✓
- [x] Ensure all A2A Protocol links use https://a2a-protocol.org/
- [x] Use consistent terminology (AgentCard, well-known, capabilities object)

## 2. Validation Script Consolidation
- [x] Consolidate to single validation script
  - [x] Delete the old scripts/validate_agent.py
  - [x] Rename scripts/validate_agent_v2.py to scripts/validate_agent.py
  - [x] Update CI workflow (validate-pr.yml) to use validate_agent.py instead of validate_agent_v2.py
  - [x] Update CLAUDE.md line 65 to use validate_agent.py (already correct)
  - [x] Update CONTRIBUTING.md line 134 to use validate_agent.py instead of validate_agent_v2.py
  - [x] Update CONTRIBUTING.md line 212 to use validate_agent.py
  - [x] Update README.md line 159 to use validate_agent.py

## 3. Python Version Standardization
- [x] Align Python version requirements across the project
  - [x] pyproject.toml: requires >=3.10 ✓
  - [x] CI workflows: uses 3.11 (keep as is, it's >=3.10)
  - [x] README.md: says 3.8+ → update to 3.10+
  - [x] Ruff config: targets py38 → update to py310
  - [x] Update all docs to consistently mention Python 3.10+

## 4. UV Migration (Priority per user request)
- [x] Migrate GitHub workflows to use astral-sh/setup-uv
  - [x] Update validate-pr.yml:
    - [x] Replace actions/setup-python@v5 with astral-sh/setup-uv@v6
    - [x] Enable cache with `enable-cache: true`
    - [x] Remove pip cache action (uv handles caching automatically)
    - [x] Change `pip install -r requirements.txt` to `uv pip install -r requirements.txt`
  - [x] Update publish.yml:
    - [x] Replace actions/setup-python@v5 with astral-sh/setup-uv@v6
    - [x] Enable cache with `enable-cache: true`
    - [x] Change pip commands to uv equivalents
    - [x] For client build: use `uv pip install build twine`
- [x] Update documentation to prefer uv commands:
  - [x] README.md: Show both uv and pip options (uv first)
  - [x] CONTRIBUTING.md: Update setup instructions to use uv primarily
  - [x] CLAUDE.md: Already uses uv ✓ (just needs validator script update)
  - [x] client-python/README.md: Show both `uv pip install` and `pip install`
  - [x] Remove references to pip cache, mention uv's automatic caching
  - [x] Note: Keep pip examples as fallback for users who prefer it

## 5. Type Checking Migration
- [x] Replace mypy with ty in client-python/pyproject.toml
  - [x] Remove mypy from dev dependencies
  - [x] Add ty as dev dependency
  - [x] Update any type checking documentation to use `uvx ty check`

## 6. Documentation Updates
- [ ] README.md updates
  - [ ] Remove Node.js prerequisite (site is static HTML/JS)
  - [ ] Update Python prerequisite from 3.8+ to 3.10+
  - [ ] Add note that GitHub Actions validation is live ✓
- [ ] CONTRIBUTING.md updates
  - [ ] Fix validator script references (after consolidation)
  - [ ] Add section on using `uvx ty check` for type checking
- [ ] CLAUDE.md updates
  - [ ] Fix validator script reference (after consolidation)
- [ ] Well-known path documentation:
  - [ ] Schema already supports both /.well-known/agent.json and /.well-known/agent-card.json ✓
  - [ ] Update README to mention both paths
  - [ ] Update CONTRIBUTING.md to show both options
  - [ ] Update CLAUDE.md to note both are supported
  - [ ] Consider noting "agent-card.json" as preferred (per A2A spec)

## 7. Registry Metadata Cleanup
- [ ] Resolve _registryMetadata vs top-level _id/_source confusion
  - [ ] generate_registry.py creates both (for backward compat)
  - [ ] Schema only defines _registryMetadata
  - [ ] Client uses agent._id (top-level)
  - [ ] Decision: Keep both for now but document deprecation plan
  - [ ] Update client to prefer _registryMetadata.id when available

## 8. Development Tooling
- [ ] Add uv.lock file for reproducible builds (optional, for full uv adoption)
- [ ] Consider adding pyproject.toml at root for scripts/ dependencies
- [ ] Add pre-commit hooks using uv for linting and formatting

## 9. Security Enhancements
- [ ] Add SSL verification flag to validators (default on)
- [ ] Improve error messages for well-known fetch failures
- [ ] Add retry logic for transient network failures
- [ ] Add rate limiting awareness

## 10. Website UI Improvements
- [ ] Enhance index.html visual design
  - [ ] Add smooth animations and transitions (fade-in for cards, etc.)
  - [ ] Add icons for agent capabilities (streaming, push notifications, etc.)
  - [ ] Improve loading state with skeleton cards
  - [ ] Add filter buttons for skills/capabilities
  - [ ] Add dark mode toggle
  - [ ] Show agent version and last updated info
  - [ ] Add tooltips for technical terms
  - [ ] Improve mobile responsiveness
  - [ ] Add subtle gradient overlays or patterns
  - [ ] Consider adding agent logos/avatars support

## 11. Client Library Enhancements (Future)
- [ ] Add helper methods for filtering by input/output modes
- [ ] Surface _registryMetadata properly
- [ ] Add async support for registry fetching
- [ ] Add caching configuration options

---

Owner: maintainers