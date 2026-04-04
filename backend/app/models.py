"""Pydantic models for API request/response validation"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class Skill(BaseModel):
    """A2A Protocol Skill definition"""
    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    examples: Optional[list[str]] = Field(default_factory=list)
    inputModes: Optional[list[str]] = Field(default_factory=list, alias="inputModes")  # noqa: N815
    outputModes: Optional[list[str]] = Field(default_factory=list, alias="outputModes")  # noqa: N815

    model_config = {"populate_by_name": True}


class Capabilities(BaseModel):
    """A2A Protocol Capabilities"""
    streaming: bool = False
    pushNotifications: bool = Field(False, alias="pushNotifications")  # noqa: N815
    stateTransitionHistory: bool = Field(False, alias="stateTransitionHistory")  # noqa: N815
    extensions: Optional[list[dict]] = None

    model_config = {"populate_by_name": True}


class Provider(BaseModel):
    """Agent provider information"""
    organization: Optional[str] = None
    url: Optional[HttpUrl] = None


class AgentBase(BaseModel):
    """Base agent model with A2A Protocol fields"""
    protocolVersion: str = Field(alias="protocolVersion")  # noqa: N815
    name: str
    description: str
    author: str
    wellKnownURI: HttpUrl = Field(alias="wellKnownURI")  # noqa: N815
    url: HttpUrl
    version: str

    provider: Optional[Provider] = None
    documentationUrl: Optional[HttpUrl] = Field(None, alias="documentationUrl")  # noqa: N815
    iconUrl: Optional[HttpUrl] = Field(None, alias="iconUrl")  # noqa: N815
    supportsAuthenticatedExtendedCard: Optional[bool] = Field(None, alias="supportsAuthenticatedExtendedCard")  # noqa: N815
    security: Optional[list[dict]] = None
    securitySchemes: Optional[dict] = Field(None, alias="securitySchemes")  # noqa: N815

    capabilities: Capabilities
    defaultInputModes: list[str] = Field(alias="defaultInputModes")  # noqa: N815
    defaultOutputModes: list[str] = Field(alias="defaultOutputModes")  # noqa: N815
    skills: list[Skill]

    # Conformance flag (NULL/True = standard, False = non-standard)
    conformance: Optional[bool] = None
    conformance_errors: Optional[list[str]] = None

    # Optional registry extensions
    homepage: Optional[HttpUrl] = None
    repository: Optional[HttpUrl] = None
    license: Optional[str] = None
    pricing: Optional[str] = None
    contact: Optional[str] = None

    model_config = {"populate_by_name": True}


class AgentCreate(AgentBase):
    """Model for creating a new agent (POST /agents) - full payload"""
    pass


class AgentRegister(BaseModel):
    """Simplified registration - just provide the wellKnownURI"""
    wellKnownURI: HttpUrl = Field(alias="wellKnownURI")  # noqa: N815

    # Optional overrides (if not in agent card)
    author: Optional[str] = None

    model_config = {"populate_by_name": True}


class AgentInDB(AgentBase):
    """Agent model as stored in database (includes metadata)"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    hidden: bool = False
    flag_count: int = 0
    maintainer_notes: Optional[str] = None


class AgentPublic(AgentInDB):
    """Public agent model with computed health metrics"""
    uptime_percentage: Optional[float] = None
    avg_response_time_ms: Optional[int] = None
    last_health_check: Optional[datetime] = None
    is_healthy: Optional[bool] = None
    status_notes: list[str] = Field(default_factory=list)


class HealthCheck(BaseModel):
    """Health check record"""
    id: int
    agent_id: UUID
    checked_at: datetime
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    success: bool
    error_message: Optional[str] = None


class HealthStatus(BaseModel):
    """Current health status for an agent"""
    agent_id: UUID
    is_healthy: bool
    uptime_percentage: float
    avg_response_time_ms: int
    last_check: datetime
    total_checks: int
    successful_checks: int


class UptimeMetrics(BaseModel):
    """Historical uptime metrics for an agent"""
    agent_id: UUID
    period_days: int = 30
    uptime_percentage: float
    avg_response_time_ms: int
    total_checks: int
    successful_checks: int
    failed_checks: int
    last_check: datetime
    history: list[HealthCheck] = Field(default_factory=list)


class RegistryStats(BaseModel):
    """Registry-wide statistics"""
    total_agents: int
    healthy_agents: int
    health_percentage: float
    new_agents_this_week: int
    new_agents_this_month: int
    total_skills: int
    trending_skills: list[dict[str, Any]] = Field(default_factory=list)
    avg_response_time_ms: int
    generated_at: datetime


class FlagReason(str, Enum):
    spam = "spam"
    harmful = "harmful"
    impersonation = "impersonation"
    other = "other"


class AgentFlag(BaseModel):
    """Community flag/report"""
    agent_id: UUID
    reason: FlagReason = FlagReason.other
    details: Optional[str] = None


class AgentFlagInDB(AgentFlag):
    """Flag record in database"""
    id: int
    flagged_at: datetime
    ip_address: Optional[str] = None
    agent_name: Optional[str] = None


class PaginatedAgents(BaseModel):
    """Paginated list of agents"""
    agents: list[AgentPublic]
    total: int
    limit: int
    offset: int
