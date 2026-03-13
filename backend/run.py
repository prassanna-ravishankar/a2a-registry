#!/usr/bin/env python3
"""Run the FastAPI application with Granian"""

from granian import Granian

from app.config import settings

if __name__ == "__main__":
    Granian(
        "app.main:app",
        address=settings.api_host,
        port=settings.api_port,
        interface="asgi",
        reload=settings.api_reload,
    ).serve()
