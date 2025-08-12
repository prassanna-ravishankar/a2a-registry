"""
A2A Registry client implementation.
"""

import time
from typing import List, Optional, Dict, Any
import requests
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
            raise RuntimeError(f"Failed to fetch registry: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to parse registry response: {e}")
    
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
        
        return {
            "version": registry.version,
            "generated": registry.generated,
            "total_agents": registry.count,
            "unique_skills": len(unique_skills),
            "unique_authors": len(unique_authors),
            "skills_list": sorted(list(unique_skills)),
            "authors_list": sorted(list(unique_authors))
        }