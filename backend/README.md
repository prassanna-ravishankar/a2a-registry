# A2A Registry Backend

FastAPI-based backend for the A2A Registry with dynamic agent registration, health monitoring, and analytics.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database URL and PostHog key
   ```

3. **Run database migrations**:
   ```bash
   psql $DATABASE_URL < migrations/versions/001_initial_schema.sql
   ```

4. **Start the API server**:
   ```bash
   uv run python run.py
   ```

   API will be available at `http://localhost:8000`
   - Docs: `http://localhost:8000/docs`
   - Health: `http://localhost:8000/health`

5. **Start the health check worker** (separate terminal):
   ```bash
   uv run python worker.py
   ```

## API Endpoints

### Agents

- `POST /agents` - Register a new agent (validates wellKnownURI)
- `GET /agents` - List agents with filtering
  - Query params: `skill`, `capability`, `author`, `limit`, `offset`
- `GET /agents/{id}` - Get agent details
- `DELETE /agents/{id}` - Delete agent (requires ownership verification)

### Health Checks

- `GET /agents/{id}/health` - Current health status (24h)
- `GET /agents/{id}/uptime` - Historical uptime metrics

### Statistics

- `GET /stats` - Registry-wide stats

### Moderation

- `POST /agents/{id}/flag` - Flag/report an agent

## Development

### Run with auto-reload:
```bash
# Edit .env: API_RELOAD=true
uv run python run.py
```

### Testing:
```bash
uv run pytest
```

### Code formatting:
```bash
uv run ruff check .
uv run ruff format .
```

## Deployment

### Kubernetes (GKE)

The backend is deployed to GKE using Helm. See `/helm/a2aregistry/` for the chart.

```bash
# Deploy to GKE
helm upgrade --install a2aregistry ./helm/a2aregistry \
  --namespace a2aregistry \
  --create-namespace \
  --set image.tag=latest

# Create secrets (required before first deploy)
kubectl create secret generic a2aregistry-secrets -n a2aregistry \
  --from-literal=DB_PASSWORD="..." \
  --from-literal=POSTHOG_API_KEY="" \
  --from-literal=SECRET_KEY="..."
```

### Docker Compose (Local Development)

```bash
docker-compose up
```

## Architecture

```
┌─────────────┐
│   FastAPI   │  ← API server (port 8000)
└──────┬──────┘
       │
┌──────┴──────┐
│  PostgreSQL │  ← Database
└──────┬──────┘
       │
┌──────┴──────┐
│   Worker    │  ← Health check service (background)
└─────────────┘
```

## Configuration

See `.env.example` for all configuration options.

Key settings:
- `DATABASE_URL` - Postgres connection string
- `POSTHOG_API_KEY` - PostHog project key for analytics
- `HEALTH_CHECK_INTERVAL_SECONDS` - How often to ping agents (default: 300)
- `CORS_ORIGINS` - Allowed frontend origins

## License

Same as parent project.
