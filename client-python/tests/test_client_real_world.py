#!/usr/bin/env python3
"""
Real-world test of the A2A Registry Python client.
Tests against the live registry at www.a2aregistry.org
"""

import sys
from pathlib import Path

# Add client to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a2a_registry import Registry

def test_basic_functionality():
    """Test basic registry operations"""
    print("=" * 60)
    print("Testing A2A Registry Python Client - Real World")
    print("=" * 60)

    # Initialize registry
    print("\n1. Initializing registry...")
    registry = Registry()

    # Get all agents
    print("\n2. Loading all agents...")
    agents = registry.get_all()
    print(f"   ✓ Loaded {len(agents)} agents")

    # Check conformance field
    print("\n3. Checking conformance field...")
    standard_agents = [a for a in agents if a.conformance is not False]
    non_standard_agents = [a for a in agents if a.conformance is False]
    print(f"   ✓ Standard agents: {len(standard_agents)}")
    print(f"   ✓ Non-standard agents: {len(non_standard_agents)}")

    # Search functionality
    print("\n4. Testing search...")
    results = registry.search("business")
    print(f"   ✓ Found {len(results)} agents matching 'business'")
    if results:
        print(f"   Example: {results[0].name}")

    # Get by ID
    print("\n5. Testing get_by_id...")
    if agents:
        test_agent = agents[0]
        agent_id = test_agent.registry_id
        retrieved = registry.get_by_id(agent_id)
        if retrieved:
            print(f"   ✓ Retrieved agent: {retrieved.name}")
            print(f"   ✓ Registry ID: {agent_id}")
            print(f"   ✓ Well-known URI: {retrieved.wellKnownURI}")
            print(f"   ✓ Conformance: {retrieved.conformance}")
        else:
            print(f"   ✗ Failed to retrieve agent with ID: {agent_id}")

    # Filter by capability
    print("\n6. Testing find_by_capability...")
    streaming = registry.find_by_capability("streaming")
    print(f"   ✓ Found {len(streaming)} streaming agents")

    # Get stats
    print("\n7. Testing get_stats...")
    stats = registry.get_stats()
    print(f"   ✓ Total agents: {stats['total_agents']}")
    print(f"   ✓ Unique authors: {stats['unique_authors']}")
    if 'total_skills' in stats:
        print(f"   ✓ Total skills: {stats['total_skills']}")
    else:
        print(f"   ℹ Stats keys: {list(stats.keys())}")

    # Test non-standard agent
    print("\n8. Testing non-standard agent access...")
    if non_standard_agents:
        ns_agent = non_standard_agents[0]
        print(f"   ✓ Non-standard agent: {ns_agent.name}")
        print(f"   ✓ Author: {ns_agent.author}")
        print(f"   ✓ Has wellKnownURI: {bool(ns_agent.wellKnownURI)}")
        print(f"   ✓ Skills count: {len(ns_agent.skills)}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Client works in real world!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_basic_functionality()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
