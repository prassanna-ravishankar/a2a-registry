#!/usr/bin/env python3
"""
Seed the database by registering agents from a list of wellKnownURIs.

Usage:
    # From a file (one URI per line)
    cd backend && uv run python ../scripts/seed_agents.py --file agents.txt

    # From command line
    cd backend && uv run python ../scripts/seed_agents.py https://example.com/.well-known/agent.json

    # From stdin
    cat agents.txt | cd backend && uv run python ../scripts/seed_agents.py --stdin

    # Export from production, seed locally
    cd backend && uv run python ../scripts/export_agents.py --api https://beta.a2aregistry.org/api | uv run python ../scripts/seed_agents.py --stdin
"""

import argparse
import asyncio
import sys
from pathlib import Path

try:
    import aiohttp
except ImportError:
    print("Error: aiohttp not installed. Run from backend directory with: cd backend && uv run python ../scripts/seed_agents.py")
    sys.exit(1)

DEFAULT_API_URL = "http://localhost:17001"


async def register_agent(session: aiohttp.ClientSession, api_url: str, well_known_uri: str) -> tuple[bool, str]:
    """Register a single agent via the API."""
    try:
        async with session.post(
            f"{api_url}/agents/register",
            json={"wellKnownURI": well_known_uri},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 201:
                data = await response.json()
                return True, f"Registered: {data.get('name', 'Unknown')}"
            elif response.status == 409:
                return True, "Already exists"
            else:
                data = await response.json()
                return False, data.get("detail", f"HTTP {response.status}")
    except aiohttp.ClientError as e:
        return False, f"Network error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


async def seed_agents(api_url: str, uris: list[str], concurrency: int = 5):
    """Seed multiple agents with rate limiting."""
    semaphore = asyncio.Semaphore(concurrency)

    async def limited_register(session: aiohttp.ClientSession, uri: str):
        async with semaphore:
            return uri, await register_agent(session, api_url, uri)

    async with aiohttp.ClientSession() as session:
        # Check API health first
        try:
            async with session.get(f"{api_url}/health") as resp:
                if resp.status != 200:
                    print(f"API not healthy at {api_url}")
                    return
        except Exception as e:
            print(f"Cannot connect to API at {api_url}: {e}")
            return

        print(f"Seeding {len(uris)} agents to {api_url}...")
        print("-" * 60)

        tasks = [limited_register(session, uri) for uri in uris]
        results = await asyncio.gather(*tasks)

        success_count = 0
        fail_count = 0

        for uri, (success, message) in results:
            status = "✅" if success else "❌"
            print(f"{status} {uri}")
            print(f"   {message}")
            if success:
                success_count += 1
            else:
                fail_count += 1

        print("-" * 60)
        print(f"Done: {success_count} succeeded, {fail_count} failed")


def main():
    parser = argparse.ArgumentParser(
        description="Seed the A2A Registry database with agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://api.example.com/.well-known/agent.json
  %(prog)s --file agents.txt
  %(prog)s --file agents.txt --api http://localhost:8000
  cat agents.txt | %(prog)s --stdin
        """,
    )
    parser.add_argument(
        "uris",
        nargs="*",
        help="wellKnownURIs to register",
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        help="File containing wellKnownURIs (one per line)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read wellKnownURIs from stdin",
    )
    parser.add_argument(
        "--api",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=5,
        help="Number of concurrent requests (default: 5)",
    )

    args = parser.parse_args()

    # Collect URIs from all sources
    uris = list(args.uris)

    if args.file:
        if not args.file.exists():
            print(f"File not found: {args.file}")
            sys.exit(1)
        with open(args.file) as f:
            uris.extend(line.strip() for line in f if line.strip() and not line.startswith("#"))

    if args.stdin:
        uris.extend(line.strip() for line in sys.stdin if line.strip() and not line.startswith("#"))

    if not uris:
        print("No URIs provided. Use --help for usage.")
        sys.exit(1)

    # Deduplicate while preserving order
    seen = set()
    unique_uris = []
    for uri in uris:
        if uri not in seen:
            seen.add(uri)
            unique_uris.append(uri)

    asyncio.run(seed_agents(args.api, unique_uris, args.concurrency))


if __name__ == "__main__":
    main()
