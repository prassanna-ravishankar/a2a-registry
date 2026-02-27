#!/usr/bin/env python3
"""Health check worker - background service to monitor agent health"""

import asyncio
import time
from pathlib import Path
from uuid import UUID

import aiohttp
import structlog

from app.config import settings
from app.database import db
from app.logging_config import configure_logging, get_logger
from app.repositories import AgentRepository, HealthCheckRepository
from app.validators import validate_agent_card

HEARTBEAT_FILE = Path("/tmp/worker-heartbeat")

configure_logging(json_logs=True)
logger = get_logger(__name__)


async def check_agent_health(
    agent_id: UUID,
    well_known_uri: str,
    session: aiohttp.ClientSession,
    health_repo: HealthCheckRepository,
    agent_repo: AgentRepository,
):
    """
    Check health of a single agent by pinging its wellKnownURI.

    Args:
        agent_id: UUID of the agent
        well_known_uri: The agent's wellKnownURI endpoint
        session: Aiohttp session for making requests
        health_repo: Repository for recording results
    """
    bound_logger = logger.bind(agent_id=agent_id)
    start_time = time.time()
    status_code = None
    success = False
    error_message = None

    try:
        async with session.get(
            well_known_uri,
            timeout=aiohttp.ClientTimeout(total=settings.health_check_timeout_seconds),
            headers={
                "User-Agent": "A2A-Registry-HealthCheck/1.0",
                "Accept": "application/json",
            },
        ) as response:
            status_code = response.status
            response_time_ms = int((time.time() - start_time) * 1000)

            # Consider 2xx responses as healthy
            success = 200 <= status_code < 300

            # Read body once for both health check and conformance validation
            card_data = None
            if success:
                try:
                    card_data = await response.json()
                except Exception:
                    pass

            # Record health check
            await health_repo.create(
                agent_id=agent_id,
                status_code=status_code,
                response_time_ms=response_time_ms,
                success=success,
                error_message=None,
            )

            if success:
                bound_logger.debug(
                    "health_check_ok", status_code=status_code, response_time_ms=response_time_ms
                )
                # Re-validate conformance from the live agent card
                if card_data is not None:
                    try:
                        errors = validate_agent_card(card_data, strict=True)
                        conformance = len(errors) == 0
                        await agent_repo.update_conformance(agent_id, conformance)
                        bound_logger.debug("conformance_updated", conformance=conformance, errors=errors[:3] if errors else [])
                    except Exception as conf_err:
                        bound_logger.warning("conformance_check_failed", error=str(conf_err))
            else:
                bound_logger.warning(
                    "health_check_degraded", status_code=status_code
                )

    except asyncio.TimeoutError:
        response_time_ms = int((time.time() - start_time) * 1000)
        error_message = f"Timeout after {response_time_ms}ms"
        await health_repo.create(
            agent_id=agent_id,
            status_code=None,
            response_time_ms=response_time_ms,
            success=False,
            error_message=error_message,
        )
        bound_logger.warning("health_check_timeout", response_time_ms=response_time_ms)

    except aiohttp.ClientError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        error_message = f"Network error: {type(e).__name__}: {str(e)[:100]}"
        await health_repo.create(
            agent_id=agent_id,
            status_code=None,
            response_time_ms=response_time_ms,
            success=False,
            error_message=error_message,
        )
        bound_logger.warning("health_check_network_error", error=error_message)

    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        error_message = f"Unexpected error: {type(e).__name__}: {str(e)[:100]}"
        await health_repo.create(
            agent_id=agent_id,
            status_code=None,
            response_time_ms=response_time_ms,
            success=False,
            error_message=error_message,
        )
        bound_logger.error("health_check_error", error=error_message)


async def health_check_cycle():
    """Run a single health check cycle for all agents"""
    logger.info("health_check_cycle_start")
    start_time = time.time()

    agent_repo = AgentRepository(db)
    health_repo = HealthCheckRepository(db)

    # Get all active agents
    try:
        agents, total = await agent_repo.list_agents(limit=10000)
        logger.info("health_check_cycle_agents", total=total)

        # Create shared session for all requests
        async with aiohttp.ClientSession() as session:
            # Check all agents concurrently (with some rate limiting)
            tasks = []
            for agent in agents:
                task = check_agent_health(
                    agent_id=agent.id,
                    well_known_uri=str(agent.wellKnownURI),
                    session=session,
                    health_repo=health_repo,
                    agent_repo=agent_repo,
                )
                tasks.append(task)

                # Process in batches of 50 to avoid overwhelming
                if len(tasks) >= 50:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks = []
                    # Small delay between batches
                    await asyncio.sleep(1)

            # Process remaining tasks
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        # Prune health_checks older than 90 days
        try:
            deleted = await db.execute(
                "DELETE FROM health_checks WHERE checked_at < NOW() - INTERVAL '90 days'"
            )
            logger.info("health_check_pruned", deleted=deleted)
        except Exception as prune_err:
            logger.warning("health_check_prune_failed", error=str(prune_err))

        elapsed = time.time() - start_time
        logger.info("health_check_cycle_done", elapsed_s=round(elapsed, 1))

        # Write heartbeat for liveness probe
        HEARTBEAT_FILE.write_text(str(time.time()))

    except Exception as e:
        logger.error("health_check_cycle_failed", error=str(e))


async def health_check_worker():
    """Main worker loop - runs health checks at configured interval"""
    logger.info("worker_starting")
    logger.info("worker_config", check_interval=settings.health_check_interval_seconds, timeout=settings.health_check_timeout_seconds)
    
    # Connect to database
    await db.connect()
    logger.info("database_connected")

    try:
        while True:
            try:
                await health_check_cycle()
            except Exception as e:
                logger.error("health_check_cycle_error", error=str(e))

            # Wait for next cycle
            logger.info("worker_sleeping", seconds=settings.health_check_interval_seconds)
            await asyncio.sleep(settings.health_check_interval_seconds)

    except KeyboardInterrupt:
        logger.info("worker_shutdown")
    finally:
        await db.disconnect()
        logger.info("database_disconnected")


if __name__ == "__main__":
    logger.info("worker_init")
    asyncio.run(health_check_worker())
