"""
New API-backed registry client for server-side filtering and health checks.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Dict, List, Optional, Set

import requests

if TYPE_CHECKING:
    import aiohttp
else:
    try:
        import aiohttp
    except ImportError:
        aiohttp = None

from .models import Agent


class APIRegistry:
    """API-backed registry client with server-side filtering"""

    DEFAULT_API_URL = "https://www.a2aregistry.org/api"
    CACHE_DURATION = 60  # 1 minute cache (shorter since backend is dynamic)

    def __init__(self, api_url: Optional[str] = None, cache_duration: Optional[int] = None):
        """
        Initialize the API Registry client.

        Args:
            api_url: Optional custom API URL (default: https://www.a2aregistry.org/api)
            cache_duration: Optional cache duration in seconds (default: 60)
        """
        self.api_url = api_url or self.DEFAULT_API_URL
        self.cache_duration = cache_duration or self.CACHE_DURATION
        self._cache: Dict[str, any] = {}
        self._cache_timestamps: Dict[str, float] = {}

    def _get_cached(self, key: str):
        """Get value from cache if valid"""
        if key in self._cache:
            if time.time() - self._cache_timestamps[key] < self.cache_duration:
                return self._cache[key]
        return None

    def _set_cache(self, key: str, value):
        """Set cache value"""
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()

    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        self._cache_timestamps.clear()

    def get_all(self, limit: int = 1000) -> List[Agent]:
        """
        Get all agents (with optional limit).

        Args:
            limit: Maximum number of agents to return

        Returns:
            List of agents
        """
        cache_key = f"all_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        response = requests.get(
            f"{self.api_url}/agents",
            params={"limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        agents = [Agent(**agent) for agent in data["agents"]]
        self._set_cache(cache_key, agents)
        return agents

    def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """
        Get agent by ID (uses server-side lookup).

        Args:
            agent_id: Agent UUID

        Returns:
            Agent if found, None otherwise
        """
        cache_key = f"id_{agent_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            response = requests.get(
                f"{self.api_url}/agents/{agent_id}",
                timeout=10,
            )
            response.raise_for_status()
            agent = Agent(**response.json())
            self._set_cache(cache_key, agent)
            return agent
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def find_by_skill(self, skill_id: str, limit: int = 50) -> List[Agent]:
        """
        Find agents by skill (server-side filtering).

        Args:
            skill_id: Skill ID to filter by
            limit: Maximum results to return

        Returns:
            List of agents with the specified skill
        """
        cache_key = f"skill_{skill_id}_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        response = requests.get(
            f"{self.api_url}/agents",
            params={"skill": skill_id, "limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        agents = [Agent(**agent) for agent in data["agents"]]
        self._set_cache(cache_key, agents)
        return agents

    def find_by_capability(self, capability: str, limit: int = 50) -> List[Agent]:
        """
        Find agents by A2A capability (server-side filtering).

        Args:
            capability: Capability name (e.g., "streaming")
            limit: Maximum results to return

        Returns:
            List of agents with the capability enabled
        """
        cache_key = f"capability_{capability}_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        response = requests.get(
            f"{self.api_url}/agents",
            params={"capability": capability, "limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        agents = [Agent(**agent) for agent in data["agents"]]
        self._set_cache(cache_key, agents)
        return agents

    def find_by_author(self, author: str, limit: int = 50) -> List[Agent]:
        """
        Find agents by author (server-side filtering).

        Args:
            author: Author name (partial match)
            limit: Maximum results to return

        Returns:
            List of agents by the author
        """
        cache_key = f"author_{author}_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        response = requests.get(
            f"{self.api_url}/agents",
            params={"author": author, "limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        agents = [Agent(**agent) for agent in data["agents"]]
        self._set_cache(cache_key, agents)
        return agents

    def get_health(self, agent_id: str) -> Dict:
        """
        Get current health status for an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Health status dict with uptime %, response time, etc.
        """
        response = requests.get(
            f"{self.api_url}/agents/{agent_id}/health",
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_uptime(self, agent_id: str, period_days: int = 30) -> Dict:
        """
        Get historical uptime metrics for an agent.

        Args:
            agent_id: Agent UUID
            period_days: Period to get metrics for (default: 30 days)

        Returns:
            Uptime metrics dict with history
        """
        response = requests.get(
            f"{self.api_url}/agents/{agent_id}/uptime",
            params={"period_days": period_days},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_stats(self) -> Dict:
        """
        Get registry-wide statistics.

        Returns:
            Stats dict with total agents, health %, trends, etc.
        """
        cache_key = "stats"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        response = requests.get(
            f"{self.api_url}/stats",
            timeout=10,
        )
        response.raise_for_status()
        stats = response.json()
        self._set_cache(cache_key, stats)
        return stats

    def register_agent(self, agent_data: Dict) -> Agent:
        """
        Register a new agent.

        Args:
            agent_data: Agent data conforming to A2A Protocol schema

        Returns:
            Created agent

        Raises:
            HTTPError if registration fails (ownership verification, etc.)
        """
        response = requests.post(
            f"{self.api_url}/agents",
            json=agent_data,
            timeout=30,  # Longer timeout for validation
        )
        response.raise_for_status()
        return Agent(**response.json())


class AsyncAPIRegistry:
    """Async API-backed registry client"""

    DEFAULT_API_URL = "https://www.a2aregistry.org/api"
    CACHE_DURATION = 60

    def __init__(
        self,
        api_url: Optional[str] = None,
        cache_duration: Optional[int] = None,
        session: Optional["aiohttp.ClientSession"] = None,
    ):
        """
        Initialize the Async API Registry client.

        Args:
            api_url: Optional custom API URL
            cache_duration: Optional cache duration in seconds
            session: Optional aiohttp session
        """
        self.api_url = api_url or self.DEFAULT_API_URL
        self.cache_duration = cache_duration or self.CACHE_DURATION
        self._session = session
        self._own_session = session is None
        self._cache: Dict[str, any] = {}
        self._cache_timestamps: Dict[str, float] = {}

    async def __aenter__(self):
        """Async context manager entry"""
        if self._own_session:
            self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._own_session and self._session is not None:
            await self._session.close()

    def _get_cached(self, key: str):
        """Get value from cache if valid"""
        if key in self._cache:
            if time.time() - self._cache_timestamps[key] < self.cache_duration:
                return self._cache[key]
        return None

    def _set_cache(self, key: str, value):
        """Set cache value"""
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()

    async def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        self._cache_timestamps.clear()

    async def get_all(self, limit: int = 1000) -> List[Agent]:
        """Get all agents"""
        cache_key = f"all_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        if aiohttp is None or self._session is None:
            raise RuntimeError("aiohttp required for async client")

        async with self._session.get(
            f"{self.api_url}/agents",
            params={"limit": limit},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            data = await response.json()

        agents = [Agent(**agent) for agent in data["agents"]]
        self._set_cache(cache_key, agents)
        return agents

    async def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        cache_key = f"id_{agent_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        if aiohttp is None or self._session is None:
            raise RuntimeError("aiohttp required for async client")

        try:
            async with self._session.get(
                f"{self.api_url}/agents/{agent_id}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                agent = Agent(**data)
                self._set_cache(cache_key, agent)
                return agent
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return None
            raise

    async def find_by_skill(self, skill_id: str, limit: int = 50) -> List[Agent]:
        """Find agents by skill (server-side filtering)"""
        cache_key = f"skill_{skill_id}_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        if aiohttp is None or self._session is None:
            raise RuntimeError("aiohttp required for async client")

        async with self._session.get(
            f"{self.api_url}/agents",
            params={"skill": skill_id, "limit": limit},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            data = await response.json()

        agents = [Agent(**agent) for agent in data["agents"]]
        self._set_cache(cache_key, agents)
        return agents

    async def get_health(self, agent_id: str) -> Dict:
        """Get current health status"""
        if aiohttp is None or self._session is None:
            raise RuntimeError("aiohttp required for async client")

        async with self._session.get(
            f"{self.api_url}/agents/{agent_id}/health",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_stats(self) -> Dict:
        """Get registry statistics"""
        cache_key = "stats"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        if aiohttp is None or self._session is None:
            raise RuntimeError("aiohttp required for async client")

        async with self._session.get(
            f"{self.api_url}/stats",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            stats = await response.json()
            self._set_cache(cache_key, stats)
            return stats
