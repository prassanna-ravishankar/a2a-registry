#!/usr/bin/env python3
"""
Test all conforming agents to validate they actually work.
Sends a simple "hello" message to each agent.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add client to path
sys.path.insert(0, str(Path(__file__).parent.parent / "client-python" / "src"))

from a2a_registry import Registry


async def test_agent(agent):
    """Test a single agent by trying to connect and send a message"""
    print(f"\n{'=' * 60}")
    print(f"Testing: {agent.name}")
    print(f"Author: {agent.author}")
    print(f"WellKnownURI: {agent.wellKnownURI}")
    print(f"{'=' * 60}")

    try:
        # Try to connect using A2A SDK
        print("  1. Connecting to agent...")
        client = await agent.async_connect()
        print("  ✓ Connection successful!")

        # Try to send a simple message
        print("  2. Sending test message...")
        response_parts = []
        async for chunk in client.send_message({
            "role": "user",
            "parts": [{"kind": "text", "text": "Hello! This is a test from A2A Registry."}],
            "messageId": uuid4().hex
        }):
            response_parts.append(chunk)

        print("  ✓ Message sent successfully!")
        print(f"  Response chunks: {len(response_parts)}")
        if response_parts:
            print(f"  First chunk: {response_parts[0]}")

        return {"agent": agent.name, "status": "success", "chunks": len(response_parts)}

    except ImportError as e:
        print(f"  ⚠️  A2A SDK not installed: {e}")
        print(f"     Install with: pip install a2a-sdk")
        return {"agent": agent.name, "status": "skip", "error": "a2a-sdk not installed"}

    except Exception as e:
        print(f"  ✗ Failed: {type(e).__name__}: {e}")
        return {"agent": agent.name, "status": "failed", "error": str(e)}


async def main():
    """Test all conforming agents"""
    print("=" * 60)
    print("Testing All Conforming A2A Agents")
    print("=" * 60)

    # Get conforming agents
    registry = Registry()
    agents = registry.get_all()
    conforming = [a for a in agents if a.conformance is not False]

    print(f"\nFound {len(conforming)} conforming agents to test\n")

    # Test each agent
    results = []
    for agent in conforming:
        result = await test_agent(agent)
        results.append(result)
        await asyncio.sleep(1)  # Be nice to servers

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    skipped = [r for r in results if r["status"] == "skip"]

    print(f"\n✅ Successful: {len(success)}")
    for r in success:
        print(f"   - {r['agent']}")

    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for r in failed:
            print(f"   - {r['agent']}: {r['error']}")

    if skipped:
        print(f"\n⚠️  Skipped: {len(skipped)}")
        for r in skipped:
            print(f"   - {r['agent']}: {r['error']}")

    print(f"\nTotal: {len(results)} agents tested")
    print("=" * 60)

    return len(failed) == 0 and len(skipped) == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
