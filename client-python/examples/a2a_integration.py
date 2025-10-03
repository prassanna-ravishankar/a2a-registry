#!/usr/bin/env python3
"""
A2A SDK Integration Examples

Demonstrates how to use the A2A Registry client in combination with the
official A2A SDK to discover and invoke agents.

Requirements:
    pip install 'a2a-registry-client[a2a]'
"""

from a2a_registry import Registry


def basic_integration():
    """Basic example: Discover and connect to an agent."""
    print("🔗 Basic A2A SDK Integration")
    print("=" * 50)

    # Step 1: Discover agents using the registry
    registry = Registry()
    agents = registry.get_all()

    if not agents:
        print("⚠️  No agents found in registry")
        return

    # Step 2: Pick an agent (e.g., first one)
    agent = agents[0]
    print(f"\n📍 Selected Agent: {agent.name}")
    print(f"   Description: {agent.description}")
    print(f"   URL: {agent.url}")

    # Step 3: Connect using the A2A SDK
    try:
        client = agent.connect()
        print(f"\n✅ Successfully created A2A client for '{agent.name}'")
        print(f"   Client type: {type(client).__name__}")
        print(f"   Ready to invoke skills!")

        # Now you can use the A2A SDK client methods:
        # - client.message.send(...)
        # - client.message.stream(...)
        # - client.tasks.get(...)
        # etc.

    except ImportError as e:
        print(f"\n❌ Error: {e}")
        print("   Install with: pip install 'a2a-registry-client[a2a]'")
    except ValueError as e:
        print(f"\n❌ Error: {e}")


def filtered_discovery():
    """Advanced example: Filter agents before connecting."""
    print("\n\n🎯 Filtered Discovery + Connection")
    print("=" * 50)

    registry = Registry()

    # Find agents with specific capabilities
    streaming_agents = registry.find_by_capability("streaming")
    print(f"\n🔍 Found {len(streaming_agents)} agents with streaming support")

    if streaming_agents:
        agent = streaming_agents[0]
        print(f"\n📍 Connecting to: {agent.name}")

        try:
            client = agent.connect()
            print(f"✅ Connected! Ready for streaming interactions")

            # Example: Use streaming capability
            # response = await client.message.stream(
            #     skill_id="chat",
            #     input={"message": "Hello!"}
            # )

        except ImportError:
            print("❌ A2A SDK not installed")


def search_and_connect():
    """Search for agents by keyword and connect."""
    print("\n\n🔎 Search + Connect Workflow")
    print("=" * 50)

    registry = Registry()

    # Search for specific agent type
    search_query = "weather"
    results = registry.search(search_query)

    print(f"\n🔍 Search results for '{search_query}': {len(results)} agents found")

    for i, agent in enumerate(results[:3], 1):  # Show first 3
        print(f"\n{i}. {agent.name}")
        print(f"   Description: {agent.description}")
        print(f"   Author: {agent.author}")
        print(f"   Skills: {', '.join(s.id for s in agent.skills[:3])}")

        # Connect to first result
        if i == 1:
            try:
                client = agent.connect()
                print(f"   ✅ Connected via A2A SDK")
            except Exception as e:
                print(f"   ⚠️  Could not connect: {e}")


def multi_agent_workflow():
    """Demonstrate connecting to multiple agents."""
    print("\n\n🤝 Multi-Agent Workflow")
    print("=" * 50)

    registry = Registry()

    # Get agents by different criteria
    text_agents = registry.find_by_input_mode("text/plain")
    print(f"\n📝 Text input agents: {len(text_agents)}")

    json_agents = registry.find_by_output_mode("application/json")
    print(f"📊 JSON output agents: {len(json_agents)}")

    # Find agents that support both
    versatile = registry.find_by_modes(
        input_mode="text/plain",
        output_mode="application/json"
    )
    print(f"⚡ Versatile agents (text in, JSON out): {len(versatile)}")

    # Connect to multiple agents
    clients = []
    for agent in versatile[:2]:  # First 2
        try:
            client = agent.connect()
            clients.append((agent.name, client))
            print(f"✅ Connected to: {agent.name}")
        except Exception as e:
            print(f"⚠️  Failed to connect to {agent.name}: {e}")

    print(f"\n🎉 Successfully connected to {len(clients)} agents")


def custom_client_config():
    """Connect with custom A2A client configuration."""
    print("\n\n⚙️  Custom Client Configuration")
    print("=" * 50)

    registry = Registry()
    agents = registry.get_all()

    if not agents:
        return

    agent = agents[0]
    print(f"\n📍 Agent: {agent.name}")

    try:
        # Pass custom configuration to A2A client
        client = agent.connect(
            # Add custom auth, timeout, etc.
            # auth={"type": "bearer", "token": "..."},
            # timeout=30,
        )
        print("✅ Connected with custom configuration")

    except ImportError:
        print("❌ A2A SDK not installed")
    except Exception as e:
        print(f"⚠️  Error: {e}")


def error_handling():
    """Demonstrate error handling in A2A integration."""
    print("\n\n🚨 Error Handling")
    print("=" * 50)

    registry = Registry()

    # Try to connect to agent without URL
    agents = registry.get_all()

    for agent in agents:
        if not agent.url:
            print(f"\n⚠️  Agent '{agent.name}' has no URL")
            try:
                client = agent.connect()
            except ValueError as e:
                print(f"   ✅ Properly caught error: {e}")
            break

    # Try to use A2A SDK when not installed
    print("\n📦 Checking A2A SDK availability...")
    try:
        from a2a import Client
        print("   ✅ A2A SDK is installed")
    except ImportError:
        print("   ⚠️  A2A SDK not found")
        print("   Install with: pip install 'a2a-registry-client[a2a]'")


if __name__ == "__main__":
    """Run all A2A integration examples."""
    print("🤖 A2A Registry + A2A SDK Integration Examples")
    print("🚀 Demonstrating seamless discovery → invocation workflow")
    print()

    try:
        basic_integration()
        filtered_discovery()
        search_and_connect()
        multi_agent_workflow()
        custom_client_config()
        error_handling()

        print("\n\n✅ All examples completed!")
        print("\n💡 Key Takeaways:")
        print("  1. Use Registry to discover agents")
        print("  2. Use agent.connect() to get an A2A SDK client")
        print("  3. Install with: pip install 'a2a-registry-client[a2a]'")
        print("  4. Filter agents by capabilities before connecting")
        print("  5. Handle errors gracefully (ImportError, ValueError)")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("\nNote: These examples require agents in the registry.")
        print("If the registry is empty, some examples may not run fully.")
