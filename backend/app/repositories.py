"""Data access layer - repository pattern for database operations"""

import json
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from .database import Database
from .models import AgentCreate, AgentInDB, AgentPublic, HealthCheck, HealthStatus, RegistryStats, UptimeMetrics


class AgentRepository:
    """Repository for agent CRUD operations"""

    def __init__(self, db: Database):
        self.db = db

    async def create(self, agent: AgentCreate) -> AgentInDB:
        """Create a new agent"""
        query = """
            INSERT INTO agents (
                protocol_version, name, description, author, well_known_uri,
                url, version, provider, documentation_url, capabilities,
                default_input_modes, default_output_modes, skills, conformance
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING *
        """

        row = await self.db.fetchrow(
            query,
            agent.protocolVersion,
            agent.name,
            agent.description,
            agent.author,
            str(agent.wellKnownURI),
            str(agent.url),
            agent.version,
            json.dumps(agent.provider.model_dump() if agent.provider else None),
            str(agent.documentationUrl) if agent.documentationUrl else None,
            json.dumps(agent.capabilities.model_dump()),
            json.dumps(agent.defaultInputModes),
            json.dumps(agent.defaultOutputModes),
            json.dumps([skill.model_dump() for skill in agent.skills]),
            agent.conformance,
        )

        return self._row_to_agent(row)

    async def get_by_id(self, agent_id: UUID) -> Optional[AgentPublic]:
        """Get agent by ID with health metrics"""
        query = """
            SELECT
                a.*,
                -- Compute health metrics from last 24 hours
                (
                    SELECT COUNT(*)::float / NULLIF(COUNT(*), 0) * 100
                    FROM health_checks hc
                    WHERE hc.agent_id = a.id
                      AND hc.checked_at > NOW() - INTERVAL '24 hours'
                      AND hc.success = true
                ) as uptime_percentage,
                (
                    SELECT AVG(response_time_ms)::int
                    FROM health_checks hc
                    WHERE hc.agent_id = a.id
                      AND hc.checked_at > NOW() - INTERVAL '24 hours'
                      AND hc.success = true
                ) as avg_response_time_ms,
                (
                    SELECT MAX(checked_at)
                    FROM health_checks hc
                    WHERE hc.agent_id = a.id
                ) as last_health_check,
                (
                    SELECT success
                    FROM health_checks hc
                    WHERE hc.agent_id = a.id
                    ORDER BY checked_at DESC
                    LIMIT 1
                ) as is_healthy
            FROM agents a
            WHERE a.id = $1 AND a.hidden = false
        """

        row = await self.db.fetchrow(query, agent_id)
        if not row:
            return None

        return self._row_to_agent_public(row)

    async def get_by_well_known_uri(self, well_known_uri: str) -> Optional[AgentInDB]:
        """Get agent by wellKnownURI"""
        query = "SELECT * FROM agents WHERE well_known_uri = $1"
        row = await self.db.fetchrow(query, well_known_uri)
        if not row:
            return None
        return self._row_to_agent(row)

    async def list_agents(
        self,
        skill: Optional[str] = None,
        capability: Optional[str] = None,
        author: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AgentPublic], int]:
        """List agents with filtering and pagination"""

        # Build WHERE clauses
        where_clauses = ["a.hidden = false"]
        params = []
        param_idx = 1

        if skill:
            where_clauses.append(f"skills::text LIKE ${param_idx}")
            params.append(f'%"id": "{skill}"%')
            param_idx += 1

        if capability:
            _VALID_CAPABILITIES = {"streaming", "pushNotifications", "stateTransitionHistory"}
            if capability not in _VALID_CAPABILITIES:
                return [], 0
            where_clauses.append(f"capabilities::jsonb ->> '{capability}' = 'true'")

        if author:
            where_clauses.append(f"author ILIKE ${param_idx}")
            params.append(f"%{author}%")
            param_idx += 1

        where_clause = " AND ".join(where_clauses)

        # Count total
        count_query = f"SELECT COUNT(*) FROM agents a WHERE {where_clause}"
        total = await self.db.fetchval(count_query, *params)

        # Fetch paginated results with health metrics
        query = f"""
            SELECT
                a.*,
                (
                    SELECT COUNT(*)::float / NULLIF(COUNT(*), 0) * 100
                    FROM health_checks hc
                    WHERE hc.agent_id = a.id
                      AND hc.checked_at > NOW() - INTERVAL '24 hours'
                      AND hc.success = true
                ) as uptime_percentage,
                (
                    SELECT AVG(response_time_ms)::int
                    FROM health_checks hc
                    WHERE hc.agent_id = a.id
                      AND hc.checked_at > NOW() - INTERVAL '24 hours'
                      AND hc.success = true
                ) as avg_response_time_ms,
                (
                    SELECT MAX(checked_at)
                    FROM health_checks hc
                    WHERE hc.agent_id = a.id
                ) as last_health_check,
                (
                    SELECT success
                    FROM health_checks hc
                    WHERE hc.agent_id = a.id
                    ORDER BY checked_at DESC
                    LIMIT 1
                ) as is_healthy
            FROM agents a
            WHERE {where_clause}
            ORDER BY a.created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """

        params.extend([limit, offset])
        rows = await self.db.fetch(query, *params)

        agents = [self._row_to_agent_public(row) for row in rows]
        return agents, total

    async def update(self, agent_id: UUID, agent: AgentCreate) -> Optional[AgentInDB]:
        """Update an existing agent's metadata from a re-fetched agent card"""
        query = """
            UPDATE agents SET
                protocol_version = $1,
                name = $2,
                description = $3,
                author = $4,
                url = $5,
                version = $6,
                provider = $7,
                documentation_url = $8,
                capabilities = $9,
                default_input_modes = $10,
                default_output_modes = $11,
                skills = $12,
                updated_at = NOW()
            WHERE id = $13 AND hidden = false
            RETURNING *
        """
        row = await self.db.fetchrow(
            query,
            agent.protocolVersion,
            agent.name,
            agent.description,
            agent.author,
            str(agent.url),
            agent.version,
            json.dumps(agent.provider.model_dump() if agent.provider else None),
            str(agent.documentationUrl) if agent.documentationUrl else None,
            json.dumps(agent.capabilities.model_dump()),
            json.dumps(agent.defaultInputModes),
            json.dumps(agent.defaultOutputModes),
            json.dumps([skill.model_dump() for skill in agent.skills]),
            agent_id,
        )
        if not row:
            return None
        return self._row_to_agent(row)

    async def delete(self, agent_id: UUID) -> bool:
        """Delete an agent (soft delete by marking hidden)"""
        query = "UPDATE agents SET hidden = true WHERE id = $1"
        result = await self.db.execute(query, agent_id)
        return result == "UPDATE 1"

    async def increment_flag_count(self, agent_id: UUID):
        """Increment flag count for an agent"""
        query = "UPDATE agents SET flag_count = flag_count + 1 WHERE id = $1"
        await self.db.execute(query, agent_id)

    def _row_to_agent(self, row) -> AgentInDB:
        """Convert database row to AgentInDB model"""
        return AgentInDB(
            id=row["id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            hidden=row["hidden"],
            flag_count=row["flag_count"],
            protocolVersion=row["protocol_version"],
            name=row["name"],
            description=row["description"],
            author=row["author"],
            wellKnownURI=row["well_known_uri"],
            url=row["url"],
            version=row["version"],
            provider=json.loads(row["provider"]) if row["provider"] else None,
            documentationUrl=row["documentation_url"],
            capabilities=json.loads(row["capabilities"]),
            defaultInputModes=json.loads(row["default_input_modes"]),
            defaultOutputModes=json.loads(row["default_output_modes"]),
            skills=json.loads(row["skills"]),
            conformance=row["conformance"],
        )

    def _row_to_agent_public(self, row) -> AgentPublic:
        """Convert database row to AgentPublic model (includes health metrics)"""
        agent = self._row_to_agent(row)
        return AgentPublic(
            **agent.model_dump(),
            uptime_percentage=row.get("uptime_percentage"),
            avg_response_time_ms=row.get("avg_response_time_ms"),
            last_health_check=row.get("last_health_check"),
            is_healthy=row.get("is_healthy"),
        )


class HealthCheckRepository:
    """Repository for health check operations"""

    def __init__(self, db: Database):
        self.db = db

    async def create(
        self,
        agent_id: UUID,
        status_code: Optional[int],
        response_time_ms: Optional[int],
        success: bool,
        error_message: Optional[str] = None,
    ) -> HealthCheck:
        """Record a health check"""
        query = """
            INSERT INTO health_checks (agent_id, status_code, response_time_ms, success, error_message)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """

        row = await self.db.fetchrow(
            query, agent_id, status_code, response_time_ms, success, error_message
        )

        return HealthCheck(
            id=row["id"],
            agent_id=row["agent_id"],
            checked_at=row["checked_at"],
            status_code=row["status_code"],
            response_time_ms=row["response_time_ms"],
            success=row["success"],
            error_message=row["error_message"],
        )

    async def get_health_status(self, agent_id: UUID) -> Optional[HealthStatus]:
        """Get current health status for an agent (last 24 hours)"""
        query = """
            SELECT
                $1 as agent_id,
                COUNT(*) FILTER (WHERE success = true) > 0 as is_healthy,
                COALESCE(
                    COUNT(*) FILTER (WHERE success = true)::float / NULLIF(COUNT(*), 0) * 100,
                    0
                ) as uptime_percentage,
                COALESCE(
                    AVG(response_time_ms) FILTER (WHERE success = true)::int,
                    0
                ) as avg_response_time_ms,
                MAX(checked_at) as last_check,
                COUNT(*) as total_checks,
                COUNT(*) FILTER (WHERE success = true) as successful_checks
            FROM health_checks
            WHERE agent_id = $1
              AND checked_at > NOW() - INTERVAL '24 hours'
        """

        row = await self.db.fetchrow(query, agent_id)
        if not row or row["total_checks"] == 0:
            return None

        return HealthStatus(
            agent_id=row["agent_id"],
            is_healthy=row["is_healthy"],
            uptime_percentage=row["uptime_percentage"],
            avg_response_time_ms=row["avg_response_time_ms"],
            last_check=row["last_check"],
            total_checks=row["total_checks"],
            successful_checks=row["successful_checks"],
        )

    async def get_uptime_metrics(
        self, agent_id: UUID, period_days: int = 30
    ) -> Optional[UptimeMetrics]:
        """Get historical uptime metrics"""
        cutoff = datetime.now() - timedelta(days=period_days)

        # Get aggregate stats
        stats_query = """
            SELECT
                COALESCE(
                    COUNT(*) FILTER (WHERE success = true)::float / NULLIF(COUNT(*), 0) * 100,
                    0
                ) as uptime_percentage,
                COALESCE(
                    AVG(response_time_ms) FILTER (WHERE success = true)::int,
                    0
                ) as avg_response_time_ms,
                COUNT(*) as total_checks,
                COUNT(*) FILTER (WHERE success = true) as successful_checks,
                COUNT(*) FILTER (WHERE success = false) as failed_checks,
                MAX(checked_at) as last_check
            FROM health_checks
            WHERE agent_id = $1 AND checked_at > $2
        """

        stats_row = await self.db.fetchrow(stats_query, agent_id, cutoff)

        if not stats_row or stats_row["total_checks"] == 0:
            return None

        # Get recent history (last 100 checks)
        history_query = """
            SELECT * FROM health_checks
            WHERE agent_id = $1 AND checked_at > $2
            ORDER BY checked_at DESC
            LIMIT 100
        """

        history_rows = await self.db.fetch(history_query, agent_id, cutoff)
        history = [
            HealthCheck(
                id=row["id"],
                agent_id=row["agent_id"],
                checked_at=row["checked_at"],
                status_code=row["status_code"],
                response_time_ms=row["response_time_ms"],
                success=row["success"],
                error_message=row["error_message"],
            )
            for row in history_rows
        ]

        return UptimeMetrics(
            agent_id=agent_id,
            period_days=period_days,
            uptime_percentage=stats_row["uptime_percentage"],
            avg_response_time_ms=stats_row["avg_response_time_ms"],
            total_checks=stats_row["total_checks"],
            successful_checks=stats_row["successful_checks"],
            failed_checks=stats_row["failed_checks"],
            last_check=stats_row["last_check"],
            history=history,
        )


class StatsRepository:
    """Repository for registry statistics"""

    def __init__(self, db: Database):
        self.db = db

    async def get_registry_stats(self) -> RegistryStats:
        """Get registry-wide statistics"""

        # Get basic counts
        basic_stats = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total_agents,
                COUNT(*) FILTER (
                    WHERE id IN (
                        SELECT DISTINCT agent_id
                        FROM health_checks
                        WHERE checked_at > NOW() - INTERVAL '1 hour'
                          AND success = true
                    )
                ) as healthy_agents
            FROM agents
            WHERE hidden = false
        """)

        total_agents = basic_stats["total_agents"]
        healthy_agents = basic_stats["healthy_agents"]
        health_percentage = (healthy_agents / total_agents * 100) if total_agents > 0 else 0

        # New agents counts
        new_this_week = await self.db.fetchval("""
            SELECT COUNT(*)
            FROM agents
            WHERE created_at > NOW() - INTERVAL '7 days'
              AND hidden = false
        """)

        new_this_month = await self.db.fetchval("""
            SELECT COUNT(*)
            FROM agents
            WHERE created_at > NOW() - INTERVAL '30 days'
              AND hidden = false
        """)

        # Total unique skills
        total_skills = await self.db.fetchval("""
            SELECT COUNT(DISTINCT skill_id)
            FROM (
                SELECT jsonb_array_elements(skills) ->> 'id' as skill_id
                FROM agents
                WHERE hidden = false
            ) skill_counts
        """)

        # Average response time (last 24 hours)
        avg_response_time = await self.db.fetchval("""
            SELECT COALESCE(AVG(response_time_ms)::int, 0)
            FROM health_checks
            WHERE checked_at > NOW() - INTERVAL '24 hours'
              AND success = true
        """)

        return RegistryStats(
            total_agents=total_agents,
            healthy_agents=healthy_agents,
            health_percentage=health_percentage,
            new_agents_this_week=new_this_week,
            new_agents_this_month=new_this_month,
            total_skills=total_skills,
            trending_skills=[],  # TODO: Implement trending calculation
            avg_response_time_ms=avg_response_time,
            generated_at=datetime.now(),
        )


class FlagRepository:
    """Repository for agent flags/reports"""

    def __init__(self, db: Database):
        self.db = db

    async def create_flag(
        self, agent_id: UUID, reason: Optional[str], ip_address: Optional[str]
    ):
        """Record a community flag"""
        query = """
            INSERT INTO agent_flags (agent_id, reason, ip_address)
            VALUES ($1, $2, $3)
            RETURNING *
        """
        await self.db.fetchrow(query, agent_id, reason, ip_address)
