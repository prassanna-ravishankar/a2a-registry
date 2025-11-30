# Archive Notice

This directory is no longer actively used for agent data storage.

## Migration to Database

**Date**: [Migration Date]
**New System**: PostgreSQL database backend

All agents from this directory have been migrated to the PostgreSQL database and are now managed through the backend API.

## What Changed

**Old System** (Git as Database):
- Agents submitted via Pull Requests
- JSON files stored in `/agents/` directory
- Static `registry.json` generated on merge
- Manual approval required

**New System** (Dynamic Backend):
- Self-service registration via `/submit` form
- Agents stored in PostgreSQL database
- Dynamic API at `/api/agents`
- Instant registration after ownership verification

## Files Preserved

These files are kept for:
- Historical reference
- Backup purposes
- Verification of migration completeness

**Total agents migrated**: 103

## Access Agent Data

To access current agent data:
- **Website**: https://www.a2aregistry.org
- **API**: https://www.a2aregistry.org/api/agents
- **Python SDK**: `from a2a_registry import APIRegistry`

---

For questions about the migration, see `/MIGRATION_STATUS.md` and `/IMPLEMENTATION_COMPLETE.md`
