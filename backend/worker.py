#!/usr/bin/env python3
"""Health check worker - background service to monitor agent health"""

import asyncio
import time
from pathlib import Path

import aiohttp

from app.agent_card import agent_create_from_card
from app.config import settings
from app.database import db
from app.logging_config import configure_logging, get_logger
from app.repositories import AgentRepository, HealthCheckRepository
from app.smoke_test import CATEGORY_NOTES, TASK_PROBE_USER_AGENT, smoke_test
from app.validators import _normalise_fields, validate_agent_card

HEARTBEAT_FILE = Path("/tmp/worker-heartbeat")

# Cycle counter for throttling dead agent checks
_cycle_count = 0
# Check dead agents every N cycles (e.g. 48 cycles * 30 min = ~daily)
DEAD_AGENT_CHECK_INTERVAL = 48
# Task probe staleness: re-probe an agent if its last `message/send` check is
# older than this. DB-backed (task_conformance_checked_at), so the schedule
# survives worker restarts — every cycle re-evaluates which agents are stale.
TASK_PROBE_STALENESS = "24 hours"

configure_logging(json_logs=True)
logger = get_logger(__name__)


# Displayed card fields the worker keeps in sync with the live card. If any of
# these drifts from what we have stored, we re-fetch the full record. Excludes
# wellKnownURI (the worker never changes an agent's discovery URL — only the PUT
# endpoint does that, with collision checks).
_REFRESHED_FIELDS = ("name", "version", "url", "protocolVersion", "description")

# System-generated maintainer notes the worker is allowed to overwrite once an
# agent's task probe flips back to WORKING. Anything not authored by the
# registry itself (i.e. a human-written note) is left untouched.
_SYSTEM_AUTHORED_NOTES = frozenset(CATEGORY_NOTES.values())


def _metadata_differs(stored, candidate) -> bool:
    """True if any displayed field on the live card differs from what we store."""
    for field in _REFRESHED_FIELDS:
        if str(getattr(stored, field, None)) != str(getattr(candidate, field, None)):
            return True
    return False


async def refresh_agent_metadata(stored, card_data: dict, agent_repo: AgentRepository) -> bool:
    """Re-sync displayed card metadata (name/version/url/protocolVersion/...) from
    the live card when it has drifted from what we store.

    The health worker fetches the raw card directly (not via fetch_agent_card),
    so we normalise field names here the same way registration does before
    building the record. Returns True if an update was written.

    Never changes the agent's wellKnownURI — discovery-URL changes only happen
    via the admin PUT endpoint, which carries collision checks the worker lacks.
    """
    normalised = _normalise_fields(card_data)
    candidate = agent_create_from_card(
        normalised,
        str(stored.wellKnownURI),
        author_fallback=stored.author,
    )
    if not _metadata_differs(stored, candidate):
        return False

    await agent_repo.update(stored.id, candidate)
    logger.info(
        "agent_metadata_refreshed",
        agent_id=stored.id,
        name_change=(stored.name, candidate.name) if stored.name != candidate.name else None,
        version_change=(stored.version, candidate.version) if stored.version != candidate.version else None,
    )
    return True


async def refresh_recovery_notes(stored, category: str, agent_repo: AgentRepository) -> bool:
    """Clear stale system-generated failure notes once an agent recovers.

    When a probe flips to WORKING but the stored maintainer_notes is an old
    system-authored failure note (e.g. a "404 Not Found" or "host down" message
    from a previous probe), refresh it to the WORKING note so the displayed
    state stops contradicting the live health/task status (#150, #153).

    Human-authored notes are never touched. Returns True if notes were changed.
    """
    if category != "WORKING":
        return False
    current = (stored.maintainer_notes or "").strip()
    # Only overwrite notes the registry itself wrote. Empty notes need no change;
    # human notes must be preserved.
    if not current or current not in _SYSTEM_AUTHORED_NOTES:
        return False
    working_note = CATEGORY_NOTES["WORKING"]
    if current == working_note:
        return False
    await agent_repo.update_maintainer_notes(stored.id, working_note)
    logger.info("recovery_notes_refreshed", agent_id=stored.id)
    return True


async def check_agent_health(
    agent,
    session: aiohttp.ClientSession,
    health_repo: HealthCheckRepository,
    agent_repo: AgentRepository,
):
    """
    Check health of a single agent by pinging its wellKnownURI.

    Args:
        agent: The stored agent record (AgentPublic) to check and, if healthy,
            refresh displayed metadata for.
        session: Aiohttp session for making requests
        health_repo: Repository for recording results
        agent_repo: Repository for recording conformance/metadata updates
    """
    agent_id = agent.id
    well_known_uri = str(agent.wellKnownURI)
    bound_logger = logger.bind(agent_id=agent_id)
    start_time = time.time()
    status_code = None
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

            if not (200 <= status_code < 300):
                # Non-2xx: unhealthy
                await health_repo.create(
                    agent_id=agent_id,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    success=False,
                    error_message=None,
                )
                bound_logger.warning("health_check_degraded", status_code=status_code)
                return

            # 2xx response — now validate it's actually a JSON agent card
            content_type = response.headers.get("Content-Type", "")
            card_data = None
            try:
                card_data = await response.json()
            except Exception:
                pass

            if card_data is None or not isinstance(card_data, dict):
                # 200 but not valid JSON — likely HTML page, not a real agent card
                error_message = f"Agent card endpoint returned {status_code} but response is not valid JSON (Content-Type: {content_type[:50]})"
                await health_repo.create(
                    agent_id=agent_id,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    success=False,
                    error_message=error_message,
                )
                bound_logger.warning("health_check_not_json", status_code=status_code, content_type=content_type[:50])
                return

            # Valid JSON response — mark healthy
            await health_repo.create(
                agent_id=agent_id,
                status_code=status_code,
                response_time_ms=response_time_ms,
                success=True,
                error_message=None,
            )
            bound_logger.debug("health_check_ok", status_code=status_code, response_time_ms=response_time_ms)

            # Re-validate conformance from the live agent card
            try:
                errors = validate_agent_card(card_data, strict=True)
                conformance = len(errors) == 0
                await agent_repo.update_conformance(agent_id, conformance, errors=errors if errors else None)
                bound_logger.debug("conformance_updated", conformance=conformance, errors=errors[:3] if errors else [])
            except Exception as conf_err:
                bound_logger.warning("conformance_check_failed", error=str(conf_err))

            # Refresh the displayed card metadata (name/version/url/protocolVersion/
            # description/skills/...) from the live card. Without this, an agent that
            # renames or version-bumps shows frozen-at-registration metadata forever,
            # even though we successfully fetch its current card every cycle (#153).
            try:
                await refresh_agent_metadata(agent, card_data, agent_repo)
            except Exception as refresh_err:
                bound_logger.warning("metadata_refresh_failed", error=str(refresh_err))

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


async def _agents_needing_task_probe(agents) -> set:
    """
    Return the set of agent_ids whose last task probe is stale (or never run).

    A single query keeps this cheap regardless of agent count. We pass in the
    candidate set so we only ever consider live (non-dead) agents.
    """
    if not agents:
        return set()
    agent_ids = [a.id for a in agents]
    rows = await db.fetch(
        f"""
        SELECT id FROM agents
        WHERE id = ANY($1::uuid[])
          AND (task_conformance_checked_at IS NULL
               OR task_conformance_checked_at < NOW() - INTERVAL '{TASK_PROBE_STALENESS}')
        """,
        agent_ids,
    )
    return {row["id"] for row in rows}


async def probe_one_task(agent, agent_repo: AgentRepository) -> str:
    """Send an A2A message/send to one agent and persist the result category."""
    bound_logger = logger.bind(agent_id=agent.id)
    try:
        category, _note, response_ms = await smoke_test(
            str(agent.wellKnownURI),
            user_agent=TASK_PROBE_USER_AGENT,
        )
        await agent_repo.update_task_conformance(agent.id, category, response_ms)
        # If the agent recovered, drop any stale system-authored failure note so
        # the displayed state stops contradicting the live result (#150, #153).
        try:
            await refresh_recovery_notes(agent, category, agent_repo)
        except Exception as note_err:
            bound_logger.warning("recovery_notes_refresh_failed", error=str(note_err))
        bound_logger.debug("task_probe_done", category=category, response_ms=response_ms)
        return category
    except Exception as exc:
        # Don't let one probe failure crash the batch.
        bound_logger.warning("task_probe_error", error=str(exc)[:120])
        return "OTHER"


async def run_task_probes(agent_repo: AgentRepository, agents) -> int:
    """
    Probe every supplied agent for A2A `message/send` conformance.

    Smaller batches than the GET health cycle (probes are slower and hit a
    real endpoint, not just an agent-card JSON file).
    """
    BATCH = 10
    PAUSE_S = 2

    total = 0
    batch: list = []
    for agent in agents:
        batch.append(probe_one_task(agent, agent_repo))
        if len(batch) >= BATCH:
            await asyncio.gather(*batch, return_exceptions=True)
            total += len(batch)
            batch = []
            await asyncio.sleep(PAUSE_S)
    if batch:
        await asyncio.gather(*batch, return_exceptions=True)
        total += len(batch)
    return total


async def health_check_cycle():
    """Run a single health check cycle for all agents"""
    global _cycle_count
    _cycle_count += 1
    logger.info("health_check_cycle_start", cycle=_cycle_count)
    start_time = time.time()

    agent_repo = AgentRepository(db)
    health_repo = HealthCheckRepository(db)

    # Get all active agents
    try:
        agents, total = await agent_repo.list_agents(limit=10000)

        # Identify agents that have failed every check in the last 24h (dead agents)
        # Only re-check these once a day instead of every cycle
        dead_agent_ids = set()
        if _cycle_count % DEAD_AGENT_CHECK_INTERVAL != 0:
            rows = await db.fetch("""
                SELECT agent_id FROM (
                    SELECT agent_id,
                           COUNT(*) FILTER (WHERE success = true) as successes
                    FROM health_checks
                    WHERE checked_at > NOW() - INTERVAL '24 hours'
                    GROUP BY agent_id
                    HAVING COUNT(*) >= 5 AND COUNT(*) FILTER (WHERE success = true) = 0
                ) dead
            """)
            dead_agent_ids = {row["agent_id"] for row in rows}

        check_agents = [a for a in agents if a.id not in dead_agent_ids]
        skipped = total - len(check_agents)
        logger.info("health_check_cycle_agents", total=total, checking=len(check_agents), skipped_dead=skipped)

        # Create shared session for all requests
        async with aiohttp.ClientSession() as session:
            # Check all agents concurrently (with some rate limiting)
            batch = []
            for agent in check_agents:
                task = check_agent_health(
                    agent,
                    session=session,
                    health_repo=health_repo,
                    agent_repo=agent_repo,
                )
                batch.append(task)

                # Process in batches of 50 to avoid overwhelming
                if len(batch) >= 50:
                    results = await asyncio.gather(*batch, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error("health_check_task_error", error=str(result))
                    batch = []
                    # Small delay between batches
                    await asyncio.sleep(1)

            # Process remaining tasks
            if batch:
                results = await asyncio.gather(*batch, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        logger.error("health_check_task_error", error=str(result))

        # Task probes: real A2A message/send via the SDK, persisted as a
        # structured category. DB-driven (re-probe agents whose last probe is
        # >24h old) instead of a cycle-counter — survives worker restarts.
        try:
            stale_ids = await _agents_needing_task_probe(check_agents)
            stale_agents = [a for a in check_agents if a.id in stale_ids]
            if stale_agents:
                probed = await run_task_probes(agent_repo, stale_agents)
                logger.info("task_probe_cycle_done", probed=probed, eligible=len(stale_agents))
        except Exception as probe_err:
            logger.warning("task_probe_cycle_failed", error=str(probe_err))

        # Prune health_checks older than 90 days
        try:
            deleted = await db.execute(
                "DELETE FROM health_checks WHERE checked_at < NOW() - INTERVAL '90 days'"
            )
            logger.info("health_check_pruned", deleted=deleted)
        except Exception as prune_err:
            logger.warning("health_check_prune_failed", error=str(prune_err))

        # Auto-hide agents that have failed every health check for 7+ days
        try:
            hidden = await db.execute("""
                UPDATE agents SET hidden = true
                WHERE hidden = false
                  AND id IN (
                    SELECT agent_id FROM (
                        SELECT agent_id,
                               COUNT(*) as total,
                               COUNT(*) FILTER (WHERE success = true) as successes,
                               MIN(checked_at) as earliest
                        FROM health_checks
                        WHERE checked_at > NOW() - INTERVAL '7 days'
                        GROUP BY agent_id
                        HAVING COUNT(*) >= 10
                           AND COUNT(*) FILTER (WHERE success = true) = 0
                    ) dead
                  )
            """)
            if hidden and hidden != "UPDATE 0":
                logger.info("auto_hidden_dead_agents", result=hidden)
        except Exception as hide_err:
            logger.warning("auto_hide_failed", error=str(hide_err))

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
