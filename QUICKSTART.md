# A2A Registry - Quick Start

Get the entire stack running in under 5 minutes with docker-compose!

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [just](https://github.com/casey/just) (optional, for convenience commands)

## Super Quick Start (Docker Compose)

```bash
# 1. Clone and enter directory
git clone <repo-url>
cd a2a-registry-server

# 2. Start everything
docker-compose up

# That's it! 🎉
# - API: http://localhost:8001
# - API Docs: http://localhost:8001/docs
# - Frontend: http://localhost:5174
# - Postgres: localhost:5433
```

The first run will:
- Build container images (~2 min)
- Create PostgreSQL database
- Run migrations
- Start all services

## Using Just Commands (Recommended)

Install just: https://github.com/casey/just

```bash
# First time setup
just setup              # Install dependencies, create .env files
just db-setup           # Create database and run migrations
just db-migrate         # Migrate existing 103 agents to DB

# Daily development
just up                 # Start all services (docker-compose)
just logs               # View all logs
just logs api           # View API logs only
just down               # Stop all services

# Or run locally without Docker
just dev                # Start API + Worker + Frontend (3 terminals)

# Other useful commands
just test-backend       # Run backend tests
just test-sdk           # Run SDK tests
just lint-backend       # Lint code
just validate-agent agents/my-agent.json  # Validate agent file
just db-stats           # View database statistics
```

## Manual Setup (Without Docker)

### 1. Install Dependencies

**Backend**:
```bash
cd backend
uv sync
```

**Frontend**:
```bash
cd website
npm install
```

### 2. Setup Database

```bash
# Create database
createdb a2a_registry

# Run migrations
psql a2a_registry < backend/migrations/versions/001_initial_schema.sql
```

### 3. Configure Environment

**Backend** (`backend/.env`):
```bash
cp backend/.env.example backend/.env
# Edit DATABASE_URL, POSTHOG_API_KEY
```

**Frontend** (`website/.env`):
```bash
cp website/.env.example website/.env
# Edit VITE_POSTHOG_KEY, VITE_API_URL
```

### 4. Run Services

**Terminal 1** - Backend API:
```bash
cd backend
uv run python run.py
# → http://localhost:8001
```

**Terminal 2** - Health Worker:
```bash
cd backend
uv run python worker.py
```

**Terminal 3** - Frontend:
```bash
cd website
npm run dev
# → http://localhost:5174
```

### 5. Migrate Existing Data

```bash
uv run python scripts/sync_to_db.py
```

## Verify Installation

**Check services are running**:
```bash
# API health check
curl http://localhost:8001/health
# → {"status":"healthy"}

# API docs
open http://localhost:8001/docs

# Frontend
open http://localhost:5174

# Database stats
just db-stats
```

## Common Commands

```bash
# View just commands
just

# Start development environment
just up                    # With Docker
just dev                   # Without Docker (local)

# Stop services
just down                  # Docker
Ctrl+C                     # Local

# View logs
just logs                  # All services
just logs api              # Specific service
docker-compose logs -f api # Alternative

# Database operations
just db-setup              # Create database
just db-migrate            # Migrate agents
just db-stats              # View stats
just db-reset              # ⚠️ Reset (deletes all data)

# Development
just test-backend          # Run tests
just lint-backend          # Lint code
just fmt-backend           # Format code
just build-backend         # Build container
just build-frontend        # Build for production

# Validate agents
just validate-agent agents/example.json
```

## Testing the API

**Register a new agent**:
```bash
curl -X POST http://localhost:8001/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "protocolVersion": "0.3.0",
    "name": "Test Agent",
    "description": "A test agent",
    "author": "Me",
    "wellKnownURI": "https://example.com/.well-known/agent.json",
    "url": "https://example.com/agent",
    "version": "1.0.0",
    "capabilities": {
      "streaming": false,
      "pushNotifications": false
    },
    "skills": [{
      "id": "test",
      "name": "Test Skill",
      "description": "Test",
      "tags": ["test"]
    }],
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"]
  }'
```

**List agents**:
```bash
curl http://localhost:8001/api/agents | jq
```

**Get stats**:
```bash
curl http://localhost:8001/api/stats | jq
```

## Troubleshooting

**Port already in use**:
```bash
# Find and kill process on port 8001
lsof -ti:8001 | xargs kill -9

# Or change ports in docker-compose.yml
```

**Database connection failed**:
```bash
# Check if postgres is running
docker-compose ps postgres

# View postgres logs
docker-compose logs postgres

# Restart postgres
docker-compose restart postgres
```

**Frontend not loading**:
```bash
# Check VITE_API_URL is correct
cat website/.env

# Rebuild frontend container
docker-compose up --build frontend
```

**Worker not running**:
```bash
# Check worker logs
docker-compose logs worker

# Worker runs health checks every 5 minutes
# Check database for health_checks table
psql a2a_registry -c "SELECT COUNT(*) FROM health_checks;"
```

## Next Steps

1. **Add your first agent**: Visit http://localhost:5174/submit
2. **Check API docs**: Visit http://localhost:8001/docs
3. **View stats**: See registry statistics at homepage
4. **Explore code**: Check out `backend/app/main.py` and `website/src/App.jsx`

## Production Deployment

See:
- `/k8s/README.md` - Kubernetes deployment
- `/.github/workflows/deploy-backend.yml` - CI/CD pipeline
- `/backend/README.md` - Backend configuration

## Getting Help

- Documentation: `/FINAL_STATUS.md`, `/IMPLEMENTATION_COMPLETE.md`
- Issues: GitHub Issues
- Backend: `/backend/README.md`
- Frontend: `/website/README.md` (if exists)
- K8s: `/k8s/README.md`
