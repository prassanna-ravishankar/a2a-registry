# Archived Scripts

This directory contains scripts that were part of the old static registry architecture.

## Deprecated Scripts

### `generate_registry.py`
**Status**: DEPRECATED
**Replaced by**: Backend API (`/backend`)

This script previously generated a static `registry.json` file from agent JSON files.

With the new backend architecture:
- Agents are stored in PostgreSQL database
- Registry data is served dynamically via REST API
- No need for static file generation

**Historical purpose**: Generated consolidated registry.json from /agents/*.json files for static GitHub Pages hosting.

---

Last used: Pre-backend migration
Archived: [Current Date]
Kept for historical reference only.
