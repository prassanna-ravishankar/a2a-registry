"""
A2A Registry client implementation.
"""

from __future__ import annotations
import time
from typing import List, Optional, Dict, Any, Set, TYPE_CHECKING
import requests

if TYPE_CHECKING:
    import aiohttp
else:
    try:
        import aiohttp
    except ImportError:
        aiohttp = None

from .models import Agent, RegistryResponse
from ._base import BaseRegistryLogic


class Registry(BaseRegistryLogic):
    """Client for interacting with the A2A Registry."""

    DEFAULT_REGISTRY_URL = "https://www.a2aregistry.org/registry.json"
    CACHE_DURATION = 300  # 5 minutes in seconds

    def __init__(self, registry_url: Optional[str] = None, cache_duration: Optional[int] = None):
        """
        Initialize the Registry client.

        Args:
            registry_url: Optional custom registry URL
            cache_duration: Optional cache duration in seconds (default: 300)
        """
        self.registry_url = registry_url or self.DEFAULT_REGISTRY_URL
        self.cache_duration = cache_duration or self.CACHE_DURATION
        self._cache: Optional[RegistryResponse] = None
        self._cache_timestamp: float = 0

    def _fetch_registry(self) -> RegistryResponse:
        """Fetch the registry from the API."""
        try:
            response = requests.get(self.registry_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return RegistryResponse(**data)
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch registry: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to parse registry response: {e}") from e

    def _get_registry(self) -> RegistryResponse:
        """Get the registry, using cache if available and valid."""
        current_time = time.time()

        if (self._cache is None or
            current_time - self._cache_timestamp > self.cache_duration):
            self._cache = self._fetch_registry()
            self._cache_timestamp = current_time

        return self._cache

    def refresh(self) -> None:
        """Force refresh the registry cache."""
        self._cache = None
        self._cache_timestamp = 0

    def get_all(self) -> List[Agent]:
        """
        Get all agents from the registry.

        Returns:
            List of all registered agents
        """
        registry = self._get_registry()
        return registry.agents

    def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """
        Get a specific agent by its ID.

        Args:
            agent_id: The agent's registry ID

        Returns:
            The agent if found, None otherwise
        """
        agents = self.get_all()
        for agent in agents:
            if agent.registry_id == agent_id:
                return agent
        return None

    def find_by_skill(self, skill_id: str) -> List[Agent]:
        """
        Find agents that have a specific skill.

        Args:
            skill_id: The skill ID to search for

        Returns:
            List of agents with the specified skill
        """
        agents = self.get_all()
        return self.filter_by_skill(agents, skill_id)

    def find_by_capability(self, capability: str) -> List[Agent]:
        """
        Find agents with a specific A2A protocol capability.

        Args:
            capability: The capability name (e.g., "streaming", "pushNotifications")

        Returns:
            List of agents with the specified capability enabled
        """
        agents = self.get_all()
        return self.filter_by_capability(agents, capability)

    def find_by_author(self, author: str) -> List[Agent]:
        """
        Find all agents by a specific author.

        Args:
            author: The author name to search for

        Returns:
            List of agents by the specified author
        """
        agents = self.get_all()
        return self.filter_by_author(agents, author)

    def find_by_input_mode(self, input_mode: str) -> List[Agent]:
        """
        Find agents that support a specific input mode.

        Args:
            input_mode: The input MIME type (e.g., "text/plain", "image/jpeg")

        Returns:
            List of agents supporting the input mode
        """
        agents = self.get_all()
        return self.filter_by_input_mode(agents, input_mode)

    def find_by_output_mode(self, output_mode: str) -> List[Agent]:
        """
        Find agents that support a specific output mode.

        Args:
            output_mode: The output MIME type (e.g., "text/plain", "application/json")

        Returns:
            List of agents supporting the output mode
        """
        agents = self.get_all()
        return self.filter_by_output_mode(agents, output_mode)

    def find_by_modes(self, input_mode: Optional[str] = None, output_mode: Optional[str] = None) -> List[Agent]:
        """
        Find agents that support specific input and/or output modes.

        Args:
            input_mode: Optional input MIME type filter
            output_mode: Optional output MIME type filter

        Returns:
            List of agents matching the criteria
        """
        agents = self.get_all()

        if input_mode:
            agents = self.filter_by_input_mode(agents, input_mode)

        if output_mode:
            agents = self.filter_by_output_mode(agents, output_mode)

        return agents

    def get_available_input_modes(self) -> Set[str]:
        """
        Get all available input modes across all agents.

        Returns:
            Set of unique input MIME types
        """
        agents = self.get_all()
        return BaseRegistryLogic.get_available_input_modes(agents)

    def get_available_output_modes(self) -> Set[str]:
        """
        Get all available output modes across all agents.

        Returns:
            Set of unique output MIME types
        """
        agents = self.get_all()
        return BaseRegistryLogic.get_available_output_modes(agents)

    def filter_agents(
        self,
        skills: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        input_modes: Optional[List[str]] = None,
        output_modes: Optional[List[str]] = None,
        authors: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        protocol_version: Optional[str] = None
    ) -> List[Agent]:
        """
        Advanced filtering of agents with multiple criteria.

        Args:
            skills: List of required skill IDs
            capabilities: List of required A2A capabilities
            input_modes: List of required input MIME types
            output_modes: List of required output MIME types
            authors: List of acceptable authors
            tags: List of required tags
            protocol_version: Required A2A protocol version

        Returns:
            List of agents matching ALL criteria
        """
        agents = self.get_all()
        return self.multi_filter_agents(
            agents, skills, capabilities, input_modes, output_modes,
            authors, tags, protocol_version
        )

    def search(self, query: str) -> List[Agent]:
        """
        Search agents by text across name, description, and skills.

        Args:
            query: The search query string

        Returns:
            List of agents matching the search query
        """
        agents = self.get_all()
        return self.search_agents(agents, query)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the registry.

        Returns:
            Dictionary with registry statistics
        """
        registry = self._get_registry()
        agents = registry.agents
        return self.compute_stats(agents, registry.version, registry.generated)

    def clear_cache(self) -> None:
        """
        Clear the registry cache. Alias for refresh() for better API consistency.
        """
        self.refresh()


class AsyncRegistry(BaseRegistryLogic):
    """Async client for interacting with the A2A Registry."""

    DEFAULT_REGISTRY_URL = "https://www.a2aregistry.org/registry.json"
    CACHE_DURATION = 300  # 5 minutes in seconds

    def __init__(self, registry_url: Optional[str] = None, cache_duration: Optional[int] = None,
                 session: Optional["aiohttp.ClientSession"] = None):
        """
        Initialize the AsyncRegistry client.

        Args:
            registry_url: Optional custom registry URL
            cache_duration: Optional cache duration in seconds (default: 300)
            session: Optional aiohttp session (will create one if not provided)
        """
        self.registry_url = registry_url or self.DEFAULT_REGISTRY_URL
        self.cache_duration = cache_duration or self.CACHE_DURATION
        self._session = session
        self._own_session = session is None
        self._cache: Optional[RegistryResponse] = None
        self._cache_timestamp: float = 0

    async def __aenter__(self):
        """Async context manager entry."""
        if self._own_session:
            self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._own_session and self._session is not None:
            await self._session.close()

    async def _fetch_registry(self) -> RegistryResponse:
        """Fetch the registry from the API."""
        if aiohttp is None:
            raise RuntimeError("aiohttp is required for AsyncRegistry. Install with: pip install 'a2a-registry-client[async]'")

        if not self._session:
            if self._own_session:
                self._session = aiohttp.ClientSession()
            else:
                raise RuntimeError("No aiohttp session available. Use async context manager or provide session.")

        try:
            async with self._session.get(self.registry_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                data = await response.json()
                return RegistryResponse(**data)
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Failed to fetch registry: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to parse registry response: {e}") from e

    async def _get_registry(self) -> RegistryResponse:
        """Get the registry, using cache if available and valid."""
        current_time = time.time()

        if (self._cache is None or
            current_time - self._cache_timestamp > self.cache_duration):
            self._cache = await self._fetch_registry()
            self._cache_timestamp = current_time

        return self._cache

    async def refresh(self) -> None:
        """Force refresh the registry cache."""
        self._cache = None
        self._cache_timestamp = 0

    async def get_all(self) -> List[Agent]:
        """
        Get all agents from the registry.

        Returns:
            List of all registered agents
        """
        registry = await self._get_registry()
        return registry.agents

    async def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """
        Get a specific agent by its ID.

        Args:
            agent_id: The agent's registry ID

        Returns:
            The agent if found, None otherwise
        """
        agents = await self.get_all()
        for agent in agents:
            if agent.registry_id == agent_id:
                return agent
        return None

    async def find_by_skill(self, skill_id: str) -> List[Agent]:
        """
        Find agents that have a specific skill.

        Args:
            skill_id: The skill ID to search for

        Returns:
            List of agents with the specified skill
        """
        agents = await self.get_all()
        return self.filter_by_skill(agents, skill_id)

    async def find_by_capability(self, capability: str) -> List[Agent]:
        """
        Find agents with a specific A2A protocol capability.

        Args:
            capability: The capability name (e.g., "streaming", "pushNotifications")

        Returns:
            List of agents with the specified capability enabled
        """
        agents = await self.get_all()
        return self.filter_by_capability(agents, capability)

    async def find_by_author(self, author: str) -> List[Agent]:
        """
        Find all agents by a specific author.

        Args:
            author: The author name to search for

        Returns:
            List of agents by the specified author
        """
        agents = await self.get_all()
        return self.filter_by_author(agents, author)

    async def find_by_input_mode(self, input_mode: str) -> List[Agent]:
        """
        Find agents that support a specific input mode.

        Args:
            input_mode: The input MIME type (e.g., "text/plain", "image/jpeg")

        Returns:
            List of agents supporting the input mode
        """
        agents = await self.get_all()
        return self.filter_by_input_mode(agents, input_mode)

    async def find_by_output_mode(self, output_mode: str) -> List[Agent]:
        """
        Find agents that support a specific output mode.

        Args:
            output_mode: The output MIME type (e.g., "text/plain", "application/json")

        Returns:
            List of agents supporting the output mode
        """
        agents = await self.get_all()
        return self.filter_by_output_mode(agents, output_mode)

    async def find_by_modes(self, input_mode: Optional[str] = None, output_mode: Optional[str] = None) -> List[Agent]:
        """
        Find agents that support specific input and/or output modes.

        Args:
            input_mode: Optional input MIME type filter
            output_mode: Optional output MIME type filter

        Returns:
            List of agents matching the criteria
        """
        agents = await self.get_all()

        if input_mode:
            agents = self.filter_by_input_mode(agents, input_mode)

        if output_mode:
            agents = self.filter_by_output_mode(agents, output_mode)

        return agents

    async def get_available_input_modes(self) -> Set[str]:
        """
        Get all available input modes across all agents.

        Returns:
            Set of unique input MIME types
        """
        agents = await self.get_all()
        return BaseRegistryLogic.get_available_input_modes(agents)

    async def get_available_output_modes(self) -> Set[str]:
        """
        Get all available output modes across all agents.

        Returns:
            Set of unique output MIME types
        """
        agents = await self.get_all()
        return BaseRegistryLogic.get_available_output_modes(agents)

    async def filter_agents(
        self,
        skills: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        input_modes: Optional[List[str]] = None,
        output_modes: Optional[List[str]] = None,
        authors: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        protocol_version: Optional[str] = None
    ) -> List[Agent]:
        """
        Advanced filtering of agents with multiple criteria.

        Args:
            skills: List of required skill IDs
            capabilities: List of required A2A capabilities
            input_modes: List of required input MIME types
            output_modes: List of required output MIME types
            authors: List of acceptable authors
            tags: List of required tags
            protocol_version: Required A2A protocol version

        Returns:
            List of agents matching ALL criteria
        """
        agents = await self.get_all()
        return self.multi_filter_agents(
            agents, skills, capabilities, input_modes, output_modes,
            authors, tags, protocol_version
        )

    async def search(self, query: str) -> List[Agent]:
        """
        Search agents by text across name, description, and skills.

        Args:
            query: The search query string

        Returns:
            List of agents matching the search query
        """
        agents = await self.get_all()
        return self.search_agents(agents, query)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the registry.

        Returns:
            Dictionary with registry statistics
        """
        registry = await self._get_registry()
        agents = registry.agents
        return self.compute_stats(agents, registry.version, registry.generated)

    async def clear_cache(self) -> None:
        """
        Clear the registry cache. Alias for refresh() for better API consistency.
        """
        await self.refresh()
