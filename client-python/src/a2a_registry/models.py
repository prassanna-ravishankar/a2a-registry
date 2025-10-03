"""
Data models for the A2A Registry client.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class Skill(BaseModel):
    """Represents a skill/capability of an agent."""
    
    id: str = Field(..., description="Unique identifier for the skill")
    name: str = Field(..., description="Human-readable name of the skill")
    description: str = Field(..., description="Detailed description of what the skill does")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    inputModes: Optional[List[str]] = Field(None, description="Supported input MIME types")
    outputModes: Optional[List[str]] = Field(None, description="Supported output MIME types")


class Capabilities(BaseModel):
    """A2A Protocol capabilities."""
    
    streaming: Optional[bool] = Field(None, description="If the agent supports SSE streaming")
    pushNotifications: Optional[bool] = Field(None, description="If the agent can push notifications")
    stateTransitionHistory: Optional[bool] = Field(None, description="If the agent exposes state history")


class Provider(BaseModel):
    """Information about the agent's service provider (A2A Provider)."""

    organization: Optional[str] = Field(None, description="The name of the organization providing the agent")

    url: Optional[HttpUrl] = Field(None, description="The URL of the organization's website")


class RegistryMetadata(BaseModel):
    """Registry-specific metadata for an agent."""
    
    id: str = Field(..., description="Registry ID (filename without extension)")
    source: str = Field(..., description="Source file path relative to registry root")


class Agent(BaseModel):
    """Represents an AI agent in the registry."""
    
    # Core A2A fields (subset, optional in client model for flexibility)
    protocolVersion: Optional[str] = Field(None, description="A2A protocol version supported by this agent")
    name: str = Field(..., description="Display name of the agent")
    description: str = Field(..., description="Brief explanation of the agent's purpose")
    url: Optional[HttpUrl] = Field(None, description="Preferred endpoint URL for interacting with the agent")

    author: str = Field(..., description="Name or handle of the creator")
    wellKnownURI: HttpUrl = Field(..., description="The /.well-known/agent.json URI")
    skills: List[Skill] = Field(..., description="List of skills the agent can perform")
    capabilities: Optional[Capabilities] = Field(None, description="A2A Protocol capabilities")
    version: Optional[str] = Field(None, description="Version of the agent")
    defaultInputModes: Optional[List[str]] = Field(None, description="Default supported input MIME types for all skills")

    defaultOutputModes: Optional[List[str]] = Field(None, description="Default supported output MIME types for all skills")

    provider: Optional[Provider] = Field(None, description="Information about the agent's service provider")
    homepage: Optional[HttpUrl] = Field(None, description="Homepage or documentation URL")
    repository: Optional[HttpUrl] = Field(None, description="Source code repository URL")
    license: Optional[str] = Field(None, description="License identifier")
    tags: Optional[List[str]] = Field(None, description="Additional tags for categorization (deprecated; use registryTags)")

    registryTags: Optional[List[str]] = Field(None, description="Additional tags for registry categorization")

    apiEndpoint: Optional[HttpUrl] = Field(None, description="Primary API endpoint")
    documentation: Optional[HttpUrl] = Field(None, description="Link to API documentation (deprecated; use documentationUrl)")

    documentationUrl: Optional[HttpUrl] = Field(None, description="An optional URL to the agent's documentation (A2A)")

    iconUrl: Optional[HttpUrl] = Field(None, description="An optional URL to an icon for the agent")

    # Registry metadata (preferred, structured format)
    registryMetadata: Optional[RegistryMetadata] = Field(None, alias="_registryMetadata", description="Registry metadata")

    # Legacy fields (maintained for backward compatibility)
    id_: Optional[str] = Field(None, alias="_id", description="Registry ID (deprecated, use registryMetadata.id)")
    source_: Optional[str] = Field(None, alias="_source", description="Source file path (deprecated, use registryMetadata.source)")
    
    @property
    def registry_id(self) -> Optional[str]:
        """Get the registry ID, preferring registryMetadata.id over legacy id_."""
        if self.registryMetadata:
            return self.registryMetadata.id
        return self.id_

    @property
    def registry_source(self) -> Optional[str]:
        """Get the registry source, preferring registryMetadata.source over legacy source_."""
        if self.registryMetadata:
            return self.registryMetadata.source
        return self.source_

    async def async_connect(self, config=None, consumers=None, interceptors=None):
        """
        Async version: Create an A2A SDK client configured for this agent.

        Requires the a2a-sdk package to be installed:
            pip install 'a2a-registry-client[a2a]'

        Args:
            config: Optional ClientConfig instance. If not provided, uses default.
            consumers: Optional list of consumer callables for handling task updates.
            interceptors: Optional list of ClientCallInterceptor instances.

        Returns:
            An initialized A2A SDK Client instance

        Raises:
            ImportError: If a2a-sdk is not installed
            ValueError: If the agent doesn't have a wellKnownURI field
            RuntimeError: If unable to fetch agent card

        Example:
            >>> from a2a_registry import AsyncRegistry
            >>> async with AsyncRegistry() as registry:
            >>>     agents = await registry.search("weather")
            >>>     client = await agents[0].async_connect()
            >>>     # Now use the A2A SDK client
        """
        try:
            from a2a.client import ClientFactory, ClientConfig, A2ACardResolver
            import httpx
        except ImportError as e:
            raise ImportError(
                "a2a-sdk is required for this feature. "
                "Install it with: pip install 'a2a-registry-client[a2a]'"
            ) from e

        if not self.wellKnownURI:
            raise ValueError(
                f"Agent '{self.name}' does not have a wellKnownURI field. "
                "Cannot create A2A client."
            )

        # Create config if not provided
        if config is None:
            config = ClientConfig()

        # Create factory
        factory = ClientFactory(config, consumers)

        # Fetch agent card from well-known URI
        try:
            # Extract base URL from wellKnownURI
            from urllib.parse import urlparse
            parsed = urlparse(str(self.wellKnownURI))
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            # Create httpx client if not provided in config
            if config.httpx_client:
                httpx_client = config.httpx_client
            else:
                httpx_client = httpx.AsyncClient()

            resolver = A2ACardResolver(httpx_client, base_url)
            # Try to get the relative path from wellKnownURI
            # e.g., from https://example.com/.well-known/agent.json extract "/.well-known/agent.json"
            relative_path = parsed.path if parsed.path else "/.well-known/agent.json"
            card = await resolver.get_agent_card(relative_card_path=relative_path)
        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch agent card from {self.wellKnownURI}: {e}"
            ) from e

        # Create and return client
        return factory.create(card, consumers, interceptors)

    def connect(self, config=None, consumers=None, interceptors=None):
        """
        Synchronous version: Create an A2A SDK client configured for this agent.

        Note: If you're already in an async context, use async_connect() instead.

        Requires the a2a-sdk package to be installed:
            pip install 'a2a-registry-client[a2a]'

        Args:
            config: Optional ClientConfig instance. If not provided, uses default.
            consumers: Optional list of consumer callables for handling task updates.
            interceptors: Optional list of ClientCallInterceptor instances.

        Returns:
            An initialized A2A SDK Client instance

        Raises:
            ImportError: If a2a-sdk is not installed
            ValueError: If the agent doesn't have a wellKnownURI field
            RuntimeError: If unable to fetch agent card or called from async context

        Example:
            >>> from a2a_registry import Registry
            >>> registry = Registry()
            >>> agent = registry.search("weather")[0]
            >>> client = agent.connect()
            >>> # Now use the A2A SDK client
        """
        try:
            import asyncio
        except ImportError as e:
            raise ImportError(
                "asyncio is required for this feature."
            ) from e

        # Check if we're in an async context
        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "connect() cannot be called from an async context. "
                "Use 'await agent.async_connect()' instead."
            )
        except RuntimeError as e:
            if "cannot be called from an async context" in str(e):
                raise
            # No running loop, we can proceed
            pass

        # Run the async version in a new event loop
        return asyncio.run(self.async_connect(config, consumers, interceptors))

    class Config:
        populate_by_name = True


class RegistryResponse(BaseModel):
    """Response from the registry API."""
    
    version: str = Field(..., description="Registry version")
    generated: str = Field(..., description="Timestamp when registry was generated")
    count: int = Field(..., description="Number of agents in the registry")
    agents: List[Agent] = Field(..., description="List of registered agents")
