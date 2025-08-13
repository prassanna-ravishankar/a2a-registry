"""
A2A Registry client implementation.
"""

import time
from typing import List, Optional, Dict, Any, Set
import requests
try:
    import aiohttp
except ImportError:
    aiohttp = None
from .models import Agent, RegistryResponse


class Registry:
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
        result = []
        
        for agent in agents:
            for skill in agent.skills:
                if skill.id == skill_id:
                    result.append(agent)
                    break
        
        return result
    
    def find_by_capability(self, capability: str) -> List[Agent]:
        """
        Find agents with a specific A2A protocol capability.
        
        Args:
            capability: The capability name (e.g., "streaming", "pushNotifications")
            
        Returns:
            List of agents with the specified capability enabled
        """
        agents = self.get_all()
        result = []
        
        for agent in agents:
            if agent.capabilities:
                cap_dict = agent.capabilities.model_dump()
                if cap_dict.get(capability) is True:
                    result.append(agent)
        
        return result
    
    def find_by_author(self, author: str) -> List[Agent]:
        """
        Find all agents by a specific author.
        
        Args:
            author: The author name to search for
            
        Returns:
            List of agents by the specified author
        """
        agents = self.get_all()
        return [agent for agent in agents if agent.author == author]
    
    def find_by_input_mode(self, input_mode: str) -> List[Agent]:
        """
        Find agents that support a specific input mode.
        
        Args:
            input_mode: The input MIME type (e.g., "text/plain", "image/jpeg")
            
        Returns:
            List of agents supporting the input mode
        """
        agents = self.get_all()
        result = []
        
        for agent in agents:
            # Check default input modes
            if agent.defaultInputModes and input_mode in agent.defaultInputModes:
                result.append(agent)
                continue
            
            # Check skill-specific input modes
            for skill in agent.skills:
                if skill.inputModes and input_mode in skill.inputModes:
                    result.append(agent)
                    break
        
        return result
    
    def find_by_output_mode(self, output_mode: str) -> List[Agent]:
        """
        Find agents that support a specific output mode.
        
        Args:
            output_mode: The output MIME type (e.g., "text/plain", "application/json")
            
        Returns:
            List of agents supporting the output mode
        """
        agents = self.get_all()
        result = []
        
        for agent in agents:
            # Check default output modes
            if agent.defaultOutputModes and output_mode in agent.defaultOutputModes:
                result.append(agent)
                continue
            
            # Check skill-specific output modes
            for skill in agent.skills:
                if skill.outputModes and output_mode in skill.outputModes:
                    result.append(agent)
                    break
        
        return result
    
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
            agents = [a for a in agents if a in self.find_by_input_mode(input_mode)]
        
        if output_mode:
            agents = [a for a in agents if a in self.find_by_output_mode(output_mode)]
        
        return agents
    
    def get_available_input_modes(self) -> Set[str]:
        """
        Get all available input modes across all agents.
        
        Returns:
            Set of unique input MIME types
        """
        agents = self.get_all()
        modes = set()
        
        for agent in agents:
            if agent.defaultInputModes:
                modes.update(agent.defaultInputModes)
            
            for skill in agent.skills:
                if skill.inputModes:
                    modes.update(skill.inputModes)
        
        return modes
    
    def get_available_output_modes(self) -> Set[str]:
        """
        Get all available output modes across all agents.
        
        Returns:
            Set of unique output MIME types
        """
        agents = self.get_all()
        modes = set()
        
        for agent in agents:
            if agent.defaultOutputModes:
                modes.update(agent.defaultOutputModes)
            
            for skill in agent.skills:
                if skill.outputModes:
                    modes.update(skill.outputModes)
        
        return modes
    
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
        
        for skill_id in skills or []:
            agents = [a for a in agents if any(s.id == skill_id for s in a.skills)]
        
        for capability in capabilities or []:
            agents = [a for a in agents if a.capabilities and 
                     getattr(a.capabilities, capability, False) is True]
        
        for input_mode in input_modes or []:
            agents = [a for a in agents if a in self.find_by_input_mode(input_mode)]
        
        for output_mode in output_modes or []:
            agents = [a for a in agents if a in self.find_by_output_mode(output_mode)]
        
        if authors:
            agents = [a for a in agents if a.author in authors]
        
        if tags:
            agents = [a for a in agents if any(
                tag in (a.registryTags or []) + (a.tags or [])
                for tag in tags
            )]
        
        if protocol_version:
            agents = [a for a in agents if a.protocolVersion == protocol_version]
        
        return agents
    
    def search(self, query: str) -> List[Agent]:
        """
        Search agents by text across name, description, and skills.
        
        Args:
            query: The search query string
            
        Returns:
            List of agents matching the search query
        """
        query_lower = query.lower()
        agents = self.get_all()
        result = []
        
        for agent in agents:
            # Search in name and description
            if (query_lower in agent.name.lower() or 
                query_lower in agent.description.lower()):
                result.append(agent)
                continue
            
            # Search in skills
            for skill in agent.skills:
                if (query_lower in skill.id.lower() or
                    query_lower in skill.name.lower() or
                    query_lower in skill.description.lower()):
                    result.append(agent)
                    break
            
            # Search in registry tags (preferred) and legacy tags
            combined_tags = []
            if getattr(agent, "registryTags", None):
                combined_tags.extend(agent.registryTags or [])
            if getattr(agent, "tags", None):
                combined_tags.extend(agent.tags or [])

            for tag in combined_tags:
                if query_lower in tag.lower():
                    result.append(agent)
                    break
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the registry.
        
        Returns:
            Dictionary with registry statistics
        """
        registry = self._get_registry()
        agents = registry.agents
        
        # Collect unique skills and authors
        unique_skills = set()
        unique_authors = set()
        
        for agent in agents:
            unique_authors.add(agent.author)
            for skill in agent.skills:
                unique_skills.add(skill.id)
        
        # Collect capabilities and protocol versions
        capabilities_count = {"streaming": 0, "pushNotifications": 0, "stateTransitionHistory": 0}
        protocol_versions = set()
        
        for agent in agents:
            if agent.capabilities:
                if agent.capabilities.streaming:
                    capabilities_count["streaming"] += 1
                if agent.capabilities.pushNotifications:
                    capabilities_count["pushNotifications"] += 1
                if agent.capabilities.stateTransitionHistory:
                    capabilities_count["stateTransitionHistory"] += 1
            
            if agent.protocolVersion:
                protocol_versions.add(agent.protocolVersion)
        
        return {
            "version": registry.version,
            "generated": registry.generated,
            "total_agents": registry.count,
            "unique_skills": len(unique_skills),
            "unique_authors": len(unique_authors),
            "capabilities_count": capabilities_count,
            "protocol_versions": sorted(list(protocol_versions)),
            "available_input_modes": sorted(list(self.get_available_input_modes())),
            "available_output_modes": sorted(list(self.get_available_output_modes())),
            "skills_list": sorted(list(unique_skills)),
            "authors_list": sorted(list(unique_authors))
        }
    
    def clear_cache(self) -> None:
        """
        Clear the registry cache. Alias for refresh() for better API consistency.
        """
        self.refresh()


class AsyncRegistry:
    """Async client for interacting with the A2A Registry."""
    
    DEFAULT_REGISTRY_URL = "https://www.a2aregistry.org/registry.json"
    CACHE_DURATION = 300  # 5 minutes in seconds
    
    def __init__(self, registry_url: Optional[str] = None, cache_duration: Optional[int] = None, 
                 session: Optional[aiohttp.ClientSession] = None):
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
        result = []
        
        for agent in agents:
            for skill in agent.skills:
                if skill.id == skill_id:
                    result.append(agent)
                    break
        
        return result
    
    async def find_by_capability(self, capability: str) -> List[Agent]:
        """
        Find agents with a specific A2A protocol capability.
        
        Args:
            capability: The capability name (e.g., "streaming", "pushNotifications")
            
        Returns:
            List of agents with the specified capability enabled
        """
        agents = await self.get_all()
        result = []
        
        for agent in agents:
            if agent.capabilities:
                cap_dict = agent.capabilities.model_dump()
                if cap_dict.get(capability) is True:
                    result.append(agent)
        
        return result
    
    async def find_by_author(self, author: str) -> List[Agent]:
        """
        Find all agents by a specific author.
        
        Args:
            author: The author name to search for
            
        Returns:
            List of agents by the specified author
        """
        agents = await self.get_all()
        return [agent for agent in agents if agent.author == author]
    
    async def find_by_input_mode(self, input_mode: str) -> List[Agent]:
        """
        Find agents that support a specific input mode.
        
        Args:
            input_mode: The input MIME type (e.g., "text/plain", "image/jpeg")
            
        Returns:
            List of agents supporting the input mode
        """
        agents = await self.get_all()
        result = []
        
        for agent in agents:
            # Check default input modes
            if agent.defaultInputModes and input_mode in agent.defaultInputModes:
                result.append(agent)
                continue
            
            # Check skill-specific input modes
            for skill in agent.skills:
                if skill.inputModes and input_mode in skill.inputModes:
                    result.append(agent)
                    break
        
        return result
    
    async def find_by_output_mode(self, output_mode: str) -> List[Agent]:
        """
        Find agents that support a specific output mode.
        
        Args:
            output_mode: The output MIME type (e.g., "text/plain", "application/json")
            
        Returns:
            List of agents supporting the output mode
        """
        agents = await self.get_all()
        result = []
        
        for agent in agents:
            # Check default output modes
            if agent.defaultOutputModes and output_mode in agent.defaultOutputModes:
                result.append(agent)
                continue
            
            # Check skill-specific output modes
            for skill in agent.skills:
                if skill.outputModes and output_mode in skill.outputModes:
                    result.append(agent)
                    break
        
        return result
    
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
            input_agents = await self.find_by_input_mode(input_mode)
            agents = [a for a in agents if a in input_agents]
        
        if output_mode:
            output_agents = await self.find_by_output_mode(output_mode)
            agents = [a for a in agents if a in output_agents]
        
        return agents
    
    async def get_available_input_modes(self) -> Set[str]:
        """
        Get all available input modes across all agents.
        
        Returns:
            Set of unique input MIME types
        """
        agents = await self.get_all()
        modes = set()
        
        for agent in agents:
            if agent.defaultInputModes:
                modes.update(agent.defaultInputModes)
            
            for skill in agent.skills:
                if skill.inputModes:
                    modes.update(skill.inputModes)
        
        return modes
    
    async def get_available_output_modes(self) -> Set[str]:
        """
        Get all available output modes across all agents.
        
        Returns:
            Set of unique output MIME types
        """
        agents = await self.get_all()
        modes = set()
        
        for agent in agents:
            if agent.defaultOutputModes:
                modes.update(agent.defaultOutputModes)
            
            for skill in agent.skills:
                if skill.outputModes:
                    modes.update(skill.outputModes)
        
        return modes
    
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
        
        for skill_id in skills or []:
            agents = [a for a in agents if any(s.id == skill_id for s in a.skills)]
        
        for capability in capabilities or []:
            agents = [a for a in agents if a.capabilities and 
                     getattr(a.capabilities, capability, False) is True]
        
        for input_mode in input_modes or []:
            input_agents = await self.find_by_input_mode(input_mode)
            agents = [a for a in agents if a in input_agents]
        
        for output_mode in output_modes or []:
            output_agents = await self.find_by_output_mode(output_mode)
            agents = [a for a in agents if a in output_agents]
        
        if authors:
            agents = [a for a in agents if a.author in authors]
        
        if tags:
            agents = [a for a in agents if any(
                tag in (a.registryTags or []) + (a.tags or [])
                for tag in tags
            )]
        
        if protocol_version:
            agents = [a for a in agents if a.protocolVersion == protocol_version]
        
        return agents
    
    async def search(self, query: str) -> List[Agent]:
        """
        Search agents by text across name, description, and skills.
        
        Args:
            query: The search query string
            
        Returns:
            List of agents matching the search query
        """
        query_lower = query.lower()
        agents = await self.get_all()
        result = []
        
        for agent in agents:
            # Search in name and description
            if (query_lower in agent.name.lower() or 
                query_lower in agent.description.lower()):
                result.append(agent)
                continue
            
            # Search in skills
            for skill in agent.skills:
                if (query_lower in skill.id.lower() or
                    query_lower in skill.name.lower() or
                    query_lower in skill.description.lower()):
                    result.append(agent)
                    break
            
            # Search in registry tags (preferred) and legacy tags
            combined_tags = []
            if getattr(agent, "registryTags", None):
                combined_tags.extend(agent.registryTags or [])
            if getattr(agent, "tags", None):
                combined_tags.extend(agent.tags or [])

            for tag in combined_tags:
                if query_lower in tag.lower():
                    result.append(agent)
                    break
        
        return result
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the registry.
        
        Returns:
            Dictionary with registry statistics
        """
        registry = await self._get_registry()
        agents = registry.agents
        
        # Collect unique skills and authors
        unique_skills = set()
        unique_authors = set()
        
        for agent in agents:
            unique_authors.add(agent.author)
            for skill in agent.skills:
                unique_skills.add(skill.id)
        
        # Collect capabilities and protocol versions
        capabilities_count = {"streaming": 0, "pushNotifications": 0, "stateTransitionHistory": 0}
        protocol_versions = set()
        
        for agent in agents:
            if agent.capabilities:
                if agent.capabilities.streaming:
                    capabilities_count["streaming"] += 1
                if agent.capabilities.pushNotifications:
                    capabilities_count["pushNotifications"] += 1
                if agent.capabilities.stateTransitionHistory:
                    capabilities_count["stateTransitionHistory"] += 1
            
            if agent.protocolVersion:
                protocol_versions.add(agent.protocolVersion)
        
        return {
            "version": registry.version,
            "generated": registry.generated,
            "total_agents": registry.count,
            "unique_skills": len(unique_skills),
            "unique_authors": len(unique_authors),
            "capabilities_count": capabilities_count,
            "protocol_versions": sorted(list(protocol_versions)),
            "available_input_modes": sorted(list(await self.get_available_input_modes())),
            "available_output_modes": sorted(list(await self.get_available_output_modes())),
            "skills_list": sorted(list(unique_skills)),
            "authors_list": sorted(list(unique_authors))
        }
    
    async def clear_cache(self) -> None:
        """
        Clear the registry cache. Alias for refresh() for better API consistency.
        """
        await self.refresh()