#!/usr/bin/env python3
"""
Export agent wellKnownURIs from the registry API.

Usage:
    # Export all agents to stdout
    cd backend && uv run python ../scripts/export_agents.py

    # Export to file
    cd backend && uv run python ../scripts/export_agents.py > agents.txt

    # Export from production
    cd backend && uv run python ../scripts/export_agents.py --api https://beta.a2aregistry.org/api
"""

import argparse
import asyncio
import sys

try:
    import aiohttp
except ImportError:
    print("Error: aiohttp not installed. Run from backend directory with: cd backend && uv run python ../scripts/export_agents.py")
    sys.exit(1)

DEFAULT_API_URL = "http://localhost:17001"


async def export_agents(api_url: str, limit: int = 1000) -> list[str]:
    """Export all agent wellKnownURIs from the API."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{api_url}/agents",
                params={"limit": limit},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    print(f"API error: HTTP {response.status}", file=sys.stderr)
                    return []

                data = await response.json()
                agents = data.get("agents", [])
                return [agent.get("wellKnownURI") for agent in agents if agent.get("wellKnownURI")]

        except aiohttp.ClientError as e:
            print(f"Network error: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return []


def main():
    parser = argparse.ArgumentParser(
        description="Export agent wellKnownURIs from the A2A Registry",
    )
    parser.add_argument(
        "--api",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of agents to export (default: 1000)",
    )

    args = parser.parse_args()

    uris = asyncio.run(export_agents(args.api, args.limit))

    if uris:
        print(f"# Exported {len(uris)} agents from {args.api}", file=sys.stderr)
        for uri in uris:
            print(uri)
    else:
        print("No agents found or error occurred", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
