"""
A2A Registry Python Client

Official Python client library for the A2A Registry.
"""

from .client import Registry
from .models import Agent, Skill, Capabilities

__version__ = "0.1.0"
__all__ = ["Registry", "Agent", "Skill", "Capabilities"]