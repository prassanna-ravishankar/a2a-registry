"""
A2A Registry Python Client

Official Python client library for the A2A Registry.
"""

from .client import Registry
from .models import Agent, Skill, Capabilities, Provider, RegistryMetadata, RegistryResponse

__version__ = "0.1.0"
__all__ = ["Registry", "Agent", "Skill", "Capabilities", "Provider", "RegistryMetadata", "RegistryResponse"]

# AsyncRegistry is available only if aiohttp is installed
try:
    from .client import AsyncRegistry
    __all__.append("AsyncRegistry")
except ImportError:
    # aiohttp not available, AsyncRegistry will not be importable
    pass