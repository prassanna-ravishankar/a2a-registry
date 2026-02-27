#!/usr/bin/env python3
"""
Fetch all agents from the registry API, hit their wellKnownURI,
and validate conformance against the A2A spec.

Usage:
    uv run scripts/check_conformance.py
    uv run scripts/check_conformance.py --strict   # full spec validation
    uv run scripts/check_conformance.py --json     # machine-readable output
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import aiohttp

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.validators import validate_agent_card

REGISTRY_API = "https://a2aregistry.org/api"
TIMEOUT = 10
CONCURRENCY = 20


@dataclass
class Result:
    name: str
    well_known_uri: str
    agent_id: str
    current_conformance: Optional[bool]
    reachable: bool = False
    status_code: Optional[int] = None
    errors: list[str] = field(default_factory=list)
    fetch_error: Optional[str] = None
    response_ms: Optional[int] = None

    @property
    def conformant(self) -> Optional[bool]:
        if not self.reachable:
            return None
        return len(self.errors) == 0


async def fetch_all_agents(session: aiohttp.ClientSession) -> list[dict]:
    agents = []
    offset = 0
    limit = 100
    while True:
        async with session.get(f"{REGISTRY_API}/agents?limit={limit}&offset={offset}") as r:
            data = await r.json()
        batch = data.get("agents", [])
        agents.extend(batch)
        if len(agents) >= data.get("total", 0) or not batch:
            break
        offset += limit
    return agents


async def check_one(agent: dict, session: aiohttp.ClientSession, strict: bool) -> Result:
    result = Result(
        name=agent["name"],
        well_known_uri=agent.get("wellKnownURI", ""),
        agent_id=agent.get("id", ""),
        current_conformance=agent.get("conformance"),
    )

    if not result.well_known_uri:
        result.fetch_error = "No wellKnownURI"
        return result

    start = time.time()
    try:
        async with session.get(
            result.well_known_uri,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT),
            headers={"User-Agent": "A2A-Registry-ConformanceCheck/1.0", "Accept": "application/json"},
            allow_redirects=True,
            ssl=False,
        ) as resp:
            result.status_code = resp.status
            result.response_ms = int((time.time() - start) * 1000)

            if resp.status != 200:
                result.fetch_error = f"HTTP {resp.status}"
                return result

            try:
                card = await resp.json(content_type=None)
            except Exception as e:
                result.fetch_error = f"Invalid JSON: {e}"
                return result

            result.reachable = True
            result.errors = validate_agent_card(card, strict=strict)

    except asyncio.TimeoutError:
        result.fetch_error = f"Timeout (>{TIMEOUT}s)"
        result.response_ms = TIMEOUT * 1000
    except aiohttp.ClientError as e:
        result.fetch_error = f"{type(e).__name__}: {str(e)[:80]}"
    except Exception as e:
        result.fetch_error = f"Unexpected: {str(e)[:80]}"

    return result


async def main(strict: bool, as_json: bool):
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    async with aiohttp.ClientSession(connector=connector) as session:
        print("Fetching agent list...", file=sys.stderr)
        agents = await fetch_all_agents(session)
        print(f"Checking {len(agents)} agents (strict={strict})...\n", file=sys.stderr)

        sem = asyncio.Semaphore(CONCURRENCY)

        async def bounded(agent):
            async with sem:
                return await check_one(agent, session, strict)

        results = await asyncio.gather(*[bounded(a) for a in agents])

    conformant     = [r for r in results if r.conformant is True]
    non_conformant = [r for r in results if r.conformant is False]
    unreachable    = [r for r in results if r.conformant is None]

    if as_json:
        out = []
        for r in sorted(results, key=lambda x: (x.conformant is not True, x.name)):
            out.append({
                "name": r.name,
                "id": r.agent_id,
                "well_known_uri": r.well_known_uri,
                "conformant": r.conformant,
                "was": r.current_conformance,
                "changed": r.conformant != r.current_conformance,
                "reachable": r.reachable,
                "status_code": r.status_code,
                "response_ms": r.response_ms,
                "errors": r.errors,
                "fetch_error": r.fetch_error,
            })
        print(json.dumps(out, indent=2))
        return

    # ── Human-readable output ─────────────────────────────────────────────────

    W = 42  # name column width

    print(f"{'='*80}")
    print(f"  A2A CONFORMANCE SCAN  (strict={strict})")
    print(f"{'='*80}\n")

    print(f"✅  CONFORMANT ({len(conformant)})")
    print(f"{'─'*60}")
    for r in sorted(conformant, key=lambda x: x.name):
        flag = " [was non-standard]" if r.current_conformance is False else ""
        print(f"  {r.name:<{W}}  {r.response_ms:>4}ms{flag}")

    print(f"\n❌  NON-CONFORMANT ({len(non_conformant)})")
    print(f"{'─'*60}")
    for r in sorted(non_conformant, key=lambda x: x.name):
        flag = " [was standard]" if r.current_conformance is True else ""
        print(f"  {r.name:<{W}}{flag}")
        for e in r.errors[:3]:
            print(f"      • {e}")
        if len(r.errors) > 3:
            print(f"      … +{len(r.errors)-3} more errors")

    print(f"\n⚠️   UNREACHABLE ({len(unreachable)})")
    print(f"{'─'*60}")
    for r in sorted(unreachable, key=lambda x: x.name):
        print(f"  {r.name:<{W}}  {r.fetch_error}")

    print(f"\n{'='*80}")
    print(f"  SUMMARY: {len(conformant)} conformant / {len(non_conformant)} non-conformant / {len(unreachable)} unreachable  (total {len(results)})")

    changed = [r for r in results if r.conformant is not None and r.conformant != r.current_conformance]
    if changed:
        print(f"\n  🔄  CHANGED since last check ({len(changed)}):")
        for r in changed:
            arrow = "✅" if r.conformant else "❌"
            print(f"      {arrow} {r.name}  ({r.current_conformance} → {r.conformant})")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Full A2A spec validation (requires all fields)")
    parser.add_argument("--json", dest="as_json", action="store_true", help="JSON output")
    args = parser.parse_args()
    asyncio.run(main(strict=args.strict, as_json=args.as_json))
