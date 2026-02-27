#!/usr/bin/env python3
"""Health check worker - background service to monitor agent health"""

import asyncio
import logging
import time
from typing import List

import aiohttp

from app.config import settings
from app.database import db
from app.repositories import AgentRepository, HealthCheckRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def check_agent_health(
    agent_id: str,
    well_known_uri: str,
    session: aiohttp.ClientSession,
    health_repo: HealthCheckRepository,
):
    """
    Check health of a single agent by pinging its wellKnownURI.

    Args:
        agent_id: UUID of the agent
        well_known_uri: The agent's wellKnownURI endpoint
        session: Aiohttp session for making requests
        health_repo: Repository for recording results
    """
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

            # Record health check
            await health_repo.create(
                agent_id=agent_id,
                status_code=status_code,
                response_time_ms=response_time_ms,
                success=success,
                error_message=None,
            )

            if success:
                logger.debug(
                    f"✅ Agent {agent_id}: {status_code} in {response_time_ms}ms"
                )
            else:
                logger.warning(
                    f"⚠️  Agent {agent_id}: HTTP {status_code}"
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
        logger.warning(f"⏱️  Agent {agent_id}: {error_message}")

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
        logger.warning(f"❌ Agent {agent_id}: {error_message}")

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
        logger.error(f"💥 Agent {agent_id}: {error_message}")


async def health_check_cycle():
    """Run a single health check cycle for all agents"""
    logger.info("🏥 Starting health check cycle")
    start_time = time.time()

    agent_repo = AgentRepository(db)
    health_repo = HealthCheckRepository(db)

    # Get all active agents
    try:
        agents, total = await agent_repo.list_agents(limit=10000)
        logger.info(f"📊 Checking health for {total} agents")

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

        elapsed = time.time() - start_time
        logger.info(f"✅ Health check cycle completed in {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"❌ Health check cycle failed: {e}")


async def health_check_worker():
    """Main worker loop - runs health checks at configured interval"""
    logger.info("🚀 Health check worker starting")
    logger.info(f"⏱️  Check interval: {settings.health_check_interval_seconds}s")
    logger.info(f"⏱️  Request timeout: {settings.health_check_timeout_seconds}s")

    # Connect to database
    await db.connect()
    logger.info("✅ Database connected")

    try:
        while True:
            try:
                await health_check_cycle()
            except Exception as e:
                logger.error(f"❌ Error in health check cycle: {e}")

            # Wait for next cycle
            logger.info(
                f"😴 Sleeping for {settings.health_check_interval_seconds}s"
            )
            await asyncio.sleep(settings.health_check_interval_seconds)

    except KeyboardInterrupt:
        logger.info("👋 Shutting down health check worker")
    finally:
        await db.disconnect()
        logger.info("👋 Database disconnected")


if __name__ == "__main__":
    logger.info("🏥 A2A Registry Health Check Worker")
    logger.info("=" * 60)
    asyncio.run(health_check_worker())
