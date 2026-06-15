#!/usr/bin/env python3
"""Health check worker - background service to monitor agent health"""

import asyncio
import time
from pathlib import Path
from typing import Optional

import aiohttp
from pydantic import HttpUrl, TypeAdapter

from app.agent_card import extract_agent_url, extract_protocol_version
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
# Displayed card fields the worker keeps in sync with the live card, mapped to
# how each is read out of a normalised card dict. Excludes wellKnownURI (only
# the admin PUT changes discovery URLs) and everything the worker can't safely
# re-derive from a card fetch (capabilities/skills/security/icon/auth flags).
_REFRESHED_FIELDS = ("name", "version", "url", "protocolVersion", "description")

# System-generated maintainer notes the worker is allowed to overwrite once an
# agent's task probe flips back to WORKING. Anything not authored by the
# registry itself (i.e. a human-written note) is left untouched.
_SYSTEM_AUTHORED_NOTES = frozenset(CATEGORY_NOTES.values())

# Coerce candidate URLs the same way the stored record does on read (the `url`
# column round-trips through AgentBase.url: HttpUrl). Without this, a card URL
# of "https://x.com" diffs forever against the stored "https://x.com/" that
# HttpUrl produces, causing a rewrite every cycle.
_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


def _canonical_url(value: str) -> str:
    """Render a URL in the same canonical form HttpUrl uses, or return it
    unchanged if it can't be parsed (the strict-validity gate already ran)."""
    try:
        return str(_HTTP_URL_ADAPTER.validate_python(value))
    except Exception:
        return value


def _raw_has(raw_card: dict, *keys: str) -> bool:
    """True if the RAW card carries a present, non-empty string under any of the
    given key spellings.

    Presence is judged against the raw (pre-normalisation) card on purpose:
    _normalise_fields injects defaults (e.g. version='1.0.0' via setdefault),
    so a normalised card always *looks* like it has a version even when the live
    card omitted it. Reading presence from the raw card is what stops a default
    from clobbering real stored data (PR #154 BLOCKING #1)."""
    for key in keys:
        value = raw_card.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def _present_card_fields(raw_card: dict, normalised: dict) -> dict[str, str]:
    """The displayed fields actually present (non-empty) in the live card.

    Presence is decided from `raw_card` (so injected defaults never count);
    values come from `normalised` (so snake_case spellings and v0.3/v1.0 shape
    differences are already resolved). A field absent from the raw card is
    omitted entirely — never written with a default.
    """
    fields: dict[str, str] = {}

    if _raw_has(raw_card, "name"):
        fields["name"] = normalised["name"]
    if _raw_has(raw_card, "version"):
        fields["version"] = normalised["version"]
    # description may legitimately be empty; only a present non-empty string is
    # authoritative, so we never blank a real stored description.
    if _raw_has(raw_card, "description"):
        fields["description"] = normalised["description"]

    # url present iff the card had a usable endpoint (top-level url or
    # interfaces[].url). The extractor raises KeyError when neither exists.
    if _raw_has(raw_card, "url", "interfaces", "supportedInterfaces"):
        try:
            url = extract_agent_url(normalised)
            if isinstance(url, str) and url.strip():
                # Canonicalise so it compares/writes stably against the stored
                # HttpUrl form (avoids per-cycle rewrites on a trailing slash).
                fields["url"] = _canonical_url(url)
        except KeyError:
            pass

    # protocolVersion: present under either spelling, or nested in interfaces.
    if _raw_has(raw_card, "protocolVersion", "protocol_version", "interfaces", "supportedInterfaces"):
        protocol_version = extract_protocol_version(normalised)
        # Sentinel 'unknown' means we couldn't actually read one — don't write it.
        if isinstance(protocol_version, str) and protocol_version not in ("", "unknown"):
            fields["protocolVersion"] = protocol_version

    return fields


async def refresh_agent_metadata(
    stored,
    card_data: dict,
    agent_repo: AgentRepository,
    *,
    conformance_errors: Optional[list] = None,
) -> bool:
    """Re-sync displayed card metadata (name/version/url/protocolVersion/
    description) from the live card when it has drifted.

    Safety invariants (data-integrity, see PR #154 review):
    - Only refreshes from a STRICT-valid card. If the live card has any
      conformance errors, we skip — a degraded-but-parseable card must not
      overwrite good stored data. Pass the strict-validation result in via
      `conformance_errors`; when omitted we compute it here.
    - Writes ONLY the five displayed fields via a column-scoped patch, never the
      full record, so provider/capabilities/skills/icon/security/auth metadata
      the worker can't re-derive are always preserved.
    - Never writes a missing/empty card field over a stored value (see
      _present_card_fields) and never changes wellKnownURI.

    Returns True if an update was written.
    """
    # _normalise_fields returns a new dict (it does not mutate card_data), so
    # card_data stays the RAW live card for presence detection.
    normalised = _normalise_fields(card_data)

    errors = conformance_errors
    if errors is None:
        errors = validate_agent_card(card_data, strict=True)
    if errors:
        # Degraded card — refresh nothing. Conformance is recorded separately.
        return False

    present = _present_card_fields(card_data, normalised)
    changed = {
        field: value
        for field, value in present.items()
        if str(getattr(stored, field, None)) != str(value)
    }
    if not changed:
        return False

    written = await agent_repo.update_card_metadata(stored.id, changed)
    if written:
        logger.info(
            "agent_metadata_refreshed",
            agent_id=stored.id,
            fields=sorted(changed.keys()),
            name_change=(stored.name, changed["name"]) if "name" in changed else None,
            version_change=(stored.version, changed["version"]) if "version" in changed else None,
        )
    return written


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
            strict_errors: Optional[list] = None
            try:
                strict_errors = validate_agent_card(card_data, strict=True)
                conformance = len(strict_errors) == 0
                await agent_repo.update_conformance(agent_id, conformance, errors=strict_errors if strict_errors else None)
                bound_logger.debug("conformance_updated", conformance=conformance, errors=strict_errors[:3] if strict_errors else [])
            except Exception as conf_err:
                bound_logger.warning("conformance_check_failed", error=str(conf_err))

            # Refresh the displayed card metadata (name/version/url/protocolVersion/
            # description) from the live card. Only from a strict-valid card, and
            # only the displayed columns — never the full record — so a degraded
            # card can't overwrite good data with defaults or NULL out fields the
            # worker can't re-derive (capabilities/skills/security/icon). See #153
            # and the PR #154 review. If conformance validation above raised,
            # strict_errors stays None and refresh_agent_metadata re-validates.
            try:
                await refresh_agent_metadata(
                    agent, card_data, agent_repo, conformance_errors=strict_errors,
                )
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
