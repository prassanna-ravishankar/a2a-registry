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
    
    # Internal fields added by the registry
    _id: Optional[str] = Field(None, alias="_id", description="Registry ID")
    _source: Optional[str] = Field(None, alias="_source", description="Source file path")
    
    class Config:
        populate_by_name = True


class RegistryResponse(BaseModel):
    """Response from the registry API."""
    
    version: str = Field(..., description="Registry version")
    generated: str = Field(..., description="Timestamp when registry was generated")
    count: int = Field(..., description="Number of agents in the registry")
    agents: List[Agent] = Field(..., description="List of registered agents")