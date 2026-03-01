FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev

COPY main.py .

ENV AGENT_URL=https://hello.a2aregistry.org
ENV PORT=8080

EXPOSE 8080

CMD ["uv", "run", "python", "main.py"]
