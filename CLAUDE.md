# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A2A Registry is a live, API-driven directory of AI agents implementing the A2A Protocol. Agents self-register via a REST API. A background worker health-checks and validates conformance every 30 minutes.

**Stack**: FastAPI + PostgreSQL (Cloud SQL) + React/Vite frontend, deployed on GKE Autopilot via Helm.

## Repository Structure

```
backend/          # FastAPI API + MCP server + background worker
  app/            # Routes, models, repositories, validators, MCP
  migrations/     # asyncpg schema migrations
  worker.py       # Health check + conformance worker
  tests/          # pytest unit + smoke tests
website/          # React/Vite frontend
client-python/    # Python SDK (a2a-registry-client on PyPI)
hello-world-agent/ # Example A2A agent deployed on Cloudflare Workers
helm/a2aregistry/ # Kubernetes Helm chart
.github/workflows/
  deploy-backend.yml        # test → build → deploy pipeline (main branch)
  deploy-hello-world-agent.yml  # deploys hello-world-agent to Cloudflare Workers
  publish.yml               # PyPI client publish
```

## Common Commands

### Backend
```bash
cd backend
uv run uvicorn app.main:app --reload   # dev server
uv run --extra dev pytest tests/ -v    # run tests
```

### Frontend
```bash
cd website
npm install && npm run dev             # dev server at http://localhost:5173
npm run build                          # production build → dist/
```

### Python Client
```bash
cd client-python
uv run pytest tests/
uv build
```

## Key Endpoints (production)

- Website: `https://a2aregistry.org`
- API: `https://a2aregistry.org/api`
- API docs: `https://a2aregistry.org/api/docs`
- MCP server: `https://a2aregistry.org/mcp/`
- PyPI: `pip install a2a-registry-client`

## Architecture Notes

- Agent registration: `POST /api/agents/register` with `{"wellKnownURI": "..."}` — backend fetches the agent card automatically
- Conformance: `true` = strict A2A spec compliant, `false` = non-conformant, `null` = not yet checked. Worker updates on each health check cycle.
- `conformance IS NOT TRUE` = non-standard (includes null/unvalidated)
- MCP server (`backend/app/mcp_server.py`) is mounted at `/mcp/` via `mcp.http_app(stateless_http=True)` — created fresh per lifespan to avoid SessionManager reuse issues in tests
- No `agents/` directory — the old "Git as database" model was replaced by the live API + PostgreSQL backend

## CI/CD

`deploy-backend.yml` runs on push to `main` when `backend/`, `website/`, or `helm/` changes:
1. **Test** — `uv run --extra dev pytest tests/ -v` (uses `astral-sh/setup-uv@v7`)
2. **Build & Push** — Docker images to GCR (api, worker, frontend)
3. **Deploy** — Helm upgrade on GKE cluster `clusterkit` in `us-central1`
4. **Purge** — Cloudflare cache purge after deploy

## Deployment

GKE Autopilot, namespace `a2aregistry`, 1 replica each (api, worker, frontend).
Resources are right-sized for a personal project — see `helm/a2aregistry/values-prod.yaml`.
Health check interval: 1800s (30 min).
