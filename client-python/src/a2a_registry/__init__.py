"""
A2A Registry Python Client

Official Python client library for the A2A Registry.
"""

from .api_client import APIRegistry
from .models import Agent, Capabilities, Provider, RegistryMetadata, RegistryResponse, Skill

__version__ = "0.4.1"
__all__ = [
    "APIRegistry", "Agent", "Skill", "Capabilities", "Provider",
    "RegistryMetadata", "RegistryResponse",
]

# Async API client (requires aiohttp)
try:
    from .api_client import AsyncAPIRegistry  # noqa: F401 — optional re-export, added to __all__
    __all__.append("AsyncAPIRegistry")
except ImportError:
    pass

# Legacy static-file clients (deprecated, use APIRegistry instead)
try:
    from .client import AsyncRegistry, Registry  # noqa: F401 — optional re-export, added to __all__
    __all__.extend(["Registry", "AsyncRegistry"])
except ImportError:
    pass
