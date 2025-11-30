# A2A Registry - Development Commands
# Install just: https://github.com/casey/just

# List available commands
default:
    @just --list

# Setup everything (first time)
setup:
    @echo "🚀 Setting up A2A Registry development environment..."
    @echo ""
    @echo "📦 Installing backend dependencies..."
    cd backend && uv sync
    @echo ""
    @echo "📦 Installing frontend dependencies..."
    cd website && npm install
    @echo ""
    @echo "📝 Creating environment files..."
    @just env-setup
    @echo ""
    @echo "✅ Setup complete!"
    @echo ""
    @echo "Next steps:"
    @echo "  1. Edit backend/.env with your DATABASE_URL and POSTHOG_API_KEY"
    @echo "  2. Edit website/.env with your VITE_POSTHOG_KEY"
    @echo "  3. Run: just db-setup"
    @echo "  4. Run: just dev"

# Create environment files if they don't exist
env-setup:
    @test -f backend/.env || cp backend/.env.example backend/.env
    @test -f website/.env || cp website/.env.example website/.env
    @echo "✅ Environment files created (edit them with your values)"

# Setup database (create + migrate)
db-setup:
    @echo "🗄️  Setting up database..."
    createdb a2a_registry || echo "Database already exists"
    psql a2a_registry < backend/migrations/versions/001_initial_schema.sql
    @echo "✅ Database ready!"

# Migrate existing agents from JSON to database
db-migrate:
    @echo "📦 Migrating agents to database..."
    uv run python scripts/sync_to_db.py
    @echo "✅ Migration complete!"

# Start all services with docker-compose
up:
    @echo "🚀 Starting all services..."
    docker-compose up

# Start services in background
up-bg:
    @echo "🚀 Starting all services in background..."
    docker-compose up -d

# Stop all services
down:
    @echo "🛑 Stopping all services..."
    docker-compose down

# View logs
logs service="":
    #!/usr/bin/env bash
    if [ -z "{{service}}" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f {{service}}
    fi

# Development mode (local, no docker)
dev:
    @echo "🔧 Starting development servers..."
    @echo ""
    @echo "Starting in 3 terminals:"
    @echo "  Terminal 1: Backend API (port 8000)"
    @echo "  Terminal 2: Health Worker"
    @echo "  Terminal 3: Frontend (port 5173)"
    @echo ""
    @just -f justfile dev-backend & just -f justfile dev-worker & just -f justfile dev-frontend

# Start backend API only
dev-backend:
    @echo "🚀 Starting backend API..."
    cd backend && uv run python run.py

# Start health worker only
dev-worker:
    @echo "🏥 Starting health check worker..."
    cd backend && uv run python worker.py

# Start frontend only
dev-frontend:
    @echo "⚛️  Starting frontend..."
    cd website && npm run dev

# Build frontend for production
build-frontend:
    @echo "📦 Building frontend..."
    cd website && npm run build
    @echo "✅ Build complete! Output in docs/"

# Build backend container
build-backend:
    @echo "🐳 Building backend container..."
    docker build -t a2a-registry-backend:latest backend/
    @echo "✅ Container built!"

# Run backend tests
test-backend:
    @echo "🧪 Running backend tests..."
    cd backend && uv run pytest

# Run Python SDK tests
test-sdk:
    @echo "🧪 Running SDK tests..."
    cd client-python && uv run pytest tests/

# Lint backend code
lint-backend:
    @echo "🔍 Linting backend..."
    cd backend && uv run ruff check .

# Format backend code
fmt-backend:
    @echo "✨ Formatting backend..."
    cd backend && uv run ruff format .

# Validate an agent file
validate-agent file:
    @echo "🔍 Validating {{file}}..."
    uv run python scripts/validate_agent.py {{file}}

# Check database connection
db-check:
    @echo "🔍 Checking database connection..."
    cd backend && uv run python -c "import asyncio; from app.database import db; asyncio.run(db.connect()); print('✅ Database connection successful!')"

# Reset database (WARNING: deletes all data)
db-reset:
    @echo "⚠️  This will delete ALL data!"
    @read -p "Are you sure? (yes/no) " confirm && [ "$$confirm" = "yes" ]
    dropdb a2a_registry || true
    @just db-setup
    @echo "✅ Database reset complete!"

# View database stats
db-stats:
    @echo "📊 Database statistics:"
    psql a2a_registry -c "SELECT COUNT(*) as agents FROM agents;"
    psql a2a_registry -c "SELECT COUNT(*) as health_checks FROM health_checks;"
    psql a2a_registry -c "SELECT COUNT(*) as flags FROM agent_flags;"

# Clean build artifacts
clean:
    @echo "🧹 Cleaning build artifacts..."
    rm -rf backend/__pycache__
    rm -rf backend/app/__pycache__
    rm -rf website/dist
    rm -rf website/node_modules/.cache
    @echo "✅ Clean complete!"

# Install just (if not already installed)
install-just:
    @echo "📦 Installing just..."
    cargo install just || curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin
    @echo "✅ just installed!"

# Show environment info
info:
    @echo "📋 Environment Information:"
    @echo ""
    @echo "Backend:"
    @cd backend && uv run python --version
    @echo ""
    @echo "Frontend:"
    @cd website && node --version
    @cd website && npm --version
    @echo ""
    @echo "Database:"
    @psql --version | head -n1
    @echo ""
    @echo "Docker:"
    @docker --version
    @docker-compose --version
