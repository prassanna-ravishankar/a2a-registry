"""
Base registry implementation with shared logic.
"""

from typing import List, Optional, Set, Dict, Any
from .models import Agent


class BaseRegistryLogic:
    """
    Base class containing all shared logic for filtering and searching agents.
    Subclasses implement the actual data fetching (sync or async).
    """

    @staticmethod
    def filter_by_skill(agents: List[Agent], skill_id: str) -> List[Agent]:
        """
        Filter agents that have a specific skill.

        Args:
            agents: List of agents to filter
            skill_id: The skill ID to search for

        Returns:
            List of agents with the specified skill
        """
        result = []
        for agent in agents:
            for skill in agent.skills:
                if skill.id == skill_id:
                    result.append(agent)
                    break
        return result

    @staticmethod
    def filter_by_capability(agents: List[Agent], capability: str) -> List[Agent]:
        """
        Filter agents with a specific A2A protocol capability.

        Args:
            agents: List of agents to filter
            capability: The capability name (e.g., "streaming", "pushNotifications")

        Returns:
            List of agents with the specified capability enabled
        """
        result = []
        for agent in agents:
            if agent.capabilities:
                cap_dict = agent.capabilities.model_dump()
                if cap_dict.get(capability) is True:
                    result.append(agent)
        return result

    @staticmethod
    def filter_by_author(agents: List[Agent], author: str) -> List[Agent]:
        """
        Filter all agents by a specific author.

        Args:
            agents: List of agents to filter
            author: The author name to search for

        Returns:
            List of agents by the specified author
        """
        return [agent for agent in agents if agent.author == author]

    @staticmethod
    def filter_by_input_mode(agents: List[Agent], input_mode: str) -> List[Agent]:
        """
        Filter agents that support a specific input mode.

        Args:
            agents: List of agents to filter
            input_mode: The input MIME type (e.g., "text/plain", "image/jpeg")

        Returns:
            List of agents supporting the input mode
        """
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

    @staticmethod
    def filter_by_output_mode(agents: List[Agent], output_mode: str) -> List[Agent]:
        """
        Filter agents that support a specific output mode.

        Args:
            agents: List of agents to filter
            output_mode: The output MIME type (e.g., "text/plain", "application/json")

        Returns:
            List of agents supporting the output mode
        """
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

    @staticmethod
    def get_available_input_modes(agents: List[Agent]) -> Set[str]:
        """
        Get all available input modes across all agents.

        Args:
            agents: List of agents to analyze

        Returns:
            Set of unique input MIME types
        """
        modes = set()
        for agent in agents:
            if agent.defaultInputModes:
                modes.update(agent.defaultInputModes)

            for skill in agent.skills:
                if skill.inputModes:
                    modes.update(skill.inputModes)
        return modes

    @staticmethod
    def get_available_output_modes(agents: List[Agent]) -> Set[str]:
        """
        Get all available output modes across all agents.

        Args:
            agents: List of agents to analyze

        Returns:
            Set of unique output MIME types
        """
        modes = set()
        for agent in agents:
            if agent.defaultOutputModes:
                modes.update(agent.defaultOutputModes)

            for skill in agent.skills:
                if skill.outputModes:
                    modes.update(skill.outputModes)
        return modes

    @staticmethod
    def search_agents(agents: List[Agent], query: str) -> List[Agent]:
        """
        Search agents by text across name, description, and skills.

        Args:
            agents: List of agents to search
            query: The search query string

        Returns:
            List of agents matching the search query
        """
        query_lower = query.lower()
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

    @staticmethod
    def multi_filter_agents(
        agents: List[Agent],
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
            agents: List of agents to filter
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
        # Start with all agents
        filtered = agents[:]

        # Apply skill filters
        for skill_id in skills or []:
            filtered = [a for a in filtered if any(s.id == skill_id for s in a.skills)]

        # Apply capability filters
        for capability in capabilities or []:
            filtered = [a for a in filtered if a.capabilities and
                       getattr(a.capabilities, capability, False) is True]

        # Apply input mode filters
        for input_mode in input_modes or []:
            filtered = BaseRegistryLogic.filter_by_input_mode(filtered, input_mode)

        # Apply output mode filters
        for output_mode in output_modes or []:
            filtered = BaseRegistryLogic.filter_by_output_mode(filtered, output_mode)

        # Apply author filter
        if authors:
            filtered = [a for a in filtered if a.author in authors]

        # Apply tags filter
        if tags:
            filtered = [a for a in filtered if any(
                tag in (a.registryTags or []) + (a.tags or [])
                for tag in tags
            )]

        # Apply protocol version filter
        if protocol_version:
            filtered = [a for a in filtered if a.protocolVersion == protocol_version]

        return filtered

    @staticmethod
    def compute_stats(agents: List[Agent], registry_version: str, registry_generated: str) -> Dict[str, Any]:
        """
        Compute statistics about the registry.

        Args:
            agents: List of agents to analyze
            registry_version: Registry version string
            registry_generated: Registry generation timestamp

        Returns:
            Dictionary with registry statistics
        """
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
            "version": registry_version,
            "generated": registry_generated,
            "total_agents": len(agents),
            "unique_skills": len(unique_skills),
            "unique_authors": len(unique_authors),
            "capabilities_count": capabilities_count,
            "protocol_versions": sorted(list(protocol_versions)),
            "available_input_modes": sorted(list(BaseRegistryLogic.get_available_input_modes(agents))),
            "available_output_modes": sorted(list(BaseRegistryLogic.get_available_output_modes(agents))),
            "skills_list": sorted(list(unique_skills)),
            "authors_list": sorted(list(unique_authors))
        }
