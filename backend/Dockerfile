FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY app ./app
COPY worker.py run.py admin_app.py run_admin.py ./

# Expose port
EXPOSE 8000

# Run API server by default
CMD ["python", "run.py"]
