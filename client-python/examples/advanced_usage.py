#!/usr/bin/env python3
"""
Advanced usage examples for the A2A Registry Python Client.

This demonstrates all the enhanced features including:
- Input/output mode filtering
- Advanced multi-criteria filtering  
- Async support
- Enhanced statistics
- Registry metadata access
"""

import asyncio
from a2a_registry import Registry


def sync_examples():
    """Demonstrate synchronous client features."""
    print("🔄 Synchronous A2A Registry Client Examples")
    print("=" * 50)
    
    # Initialize client
    registry = Registry()
    
    # Get enhanced statistics
    print("\n📊 Enhanced Registry Statistics:")
    stats = registry.get_stats()
    print(f"  Total Agents: {stats['total_agents']}")
    print(f"  Unique Skills: {stats['unique_skills']}")
    print(f"  Unique Authors: {stats['unique_authors']}")
    print(f"  Capabilities Count: {stats['capabilities_count']}")
    print(f"  Protocol Versions: {stats['protocol_versions']}")
    print(f"  Available Input Modes: {len(stats['available_input_modes'])}")
    print(f"  Available Output Modes: {len(stats['available_output_modes'])}")
    
    # Filter by input/output modes
    print("\n🎯 Input/Output Mode Filtering:")
    text_agents = registry.find_by_input_mode("text/plain")
    print(f"  Agents supporting text/plain input: {len(text_agents)}")
    
    json_agents = registry.find_by_output_mode("application/json")
    print(f"  Agents supporting JSON output: {len(json_agents)}")
    
    # Multi-mode filtering
    versatile_agents = registry.find_by_modes(
        input_mode="text/plain", 
        output_mode="application/json"
    )
    print(f"  Agents supporting both text input and JSON output: {len(versatile_agents)}")
    
    # Advanced multi-criteria filtering
    print("\n🔍 Advanced Multi-Criteria Filtering:")
    filtered_agents = registry.filter_agents(
        capabilities=["streaming"],
        input_modes=["text/plain"],
        protocol_version="1.0"
    )
    print(f"  Streaming agents with text input on A2A v1.0: {len(filtered_agents)}")
    
    # Get available modes for discovery
    print("\n🌐 Available Modes Discovery:")
    input_modes = registry.get_available_input_modes()
    output_modes = registry.get_available_output_modes()
    print(f"  All available input modes: {sorted(list(input_modes))}")
    print(f"  All available output modes: {sorted(list(output_modes))}")
    
    # Registry metadata access
    print("\n🏷️ Registry Metadata Access:")
    all_agents = registry.get_all()
    for agent in all_agents[:3]:  # Show first 3
        print(f"  {agent.name}:")
        print(f"    Registry ID: {agent.registry_id}")
        print(f"    Registry Source: {agent.registry_source}")
        if agent._registryMetadata:
            print(f"    Using new metadata format ✓")
        elif agent._id or agent._source:
            print(f"    Using legacy metadata format")


async def async_examples():
    """Demonstrate asynchronous client features."""
    print("\n⚡ Asynchronous A2A Registry Client Examples")
    print("=" * 50)
    
    try:
        from a2a_registry import AsyncRegistry
    except ImportError:
        print("❌ AsyncRegistry not available. Install with: pip install 'a2a-registry-client[async]'")
        return
    
    # Use async context manager for proper session management
    async with AsyncRegistry() as registry:
        # All the same methods, but async!
        print("\n📊 Async Enhanced Statistics:")
        stats = await registry.get_stats()
        print(f"  Total Agents: {stats['total_agents']}")
        print(f"  Capabilities: {stats['capabilities_count']}")
        
        # Async search and filtering
        print("\n🔍 Async Search and Filtering:")
        search_results = await registry.search("weather")
        print(f"  Weather-related agents: {len(search_results)}")
        
        # Async multi-criteria filtering
        streaming_agents = await registry.filter_agents(
            capabilities=["streaming", "pushNotifications"]
        )
        print(f"  Agents with streaming AND push notifications: {len(streaming_agents)}")
        
        # Async mode discovery
        input_modes = await registry.get_available_input_modes()
        print(f"  Input modes discovered asynchronously: {len(input_modes)}")


def caching_examples():
    """Demonstrate caching functionality."""
    print("\n💾 Caching and Performance Examples")
    print("=" * 50)
    
    # Custom cache duration
    registry = Registry(cache_duration=600)  # 10 minutes
    print("  ✓ Created registry with 10-minute cache")
    
    # Manual cache control
    stats1 = registry.get_stats()
    print(f"  First call (cache miss): {stats1['total_agents']} agents")
    
    stats2 = registry.get_stats()
    print(f"  Second call (cache hit): {stats2['total_agents']} agents")
    
    # Clear cache when needed
    registry.clear_cache()
    print("  ✓ Cache cleared manually")
    
    stats3 = registry.get_stats()
    print(f"  Third call (cache miss again): {stats3['total_agents']} agents")


def error_handling_examples():
    """Demonstrate error handling."""
    print("\n🚨 Error Handling Examples")
    print("=" * 50)
    
    # Invalid registry URL
    try:
        invalid_registry = Registry(registry_url="https://invalid-url-that-does-not-exist.com/registry.json")
        invalid_registry.get_all()
    except RuntimeError as e:
        print(f"  ✓ Caught expected error: {str(e)[:50]}...")
    
    # Graceful degradation
    registry = Registry()
    try:
        # This will work if registry is available
        agents = registry.get_all()
        print(f"  ✓ Successfully loaded {len(agents)} agents")
    except RuntimeError as e:
        print(f"  ⚠️  Registry unavailable: {str(e)[:50]}...")


if __name__ == "__main__":
    """Run all examples."""
    print("🤖 A2A Registry Client - Advanced Usage Examples")
    print("🚀 Showcasing all the enhanced features!")
    print()
    
    try:
        # Sync examples
        sync_examples()
        
        # Async examples  
        asyncio.run(async_examples())
        
        # Caching examples
        caching_examples()
        
        # Error handling
        error_handling_examples()
        
        print("\n✅ All examples completed successfully!")
        print("\n💡 Tips:")
        print("  - Use AsyncRegistry for high-performance applications")
        print("  - Leverage input/output mode filtering for precise agent discovery")
        print("  - Use multi-criteria filtering to find exactly what you need")
        print("  - Cache duration is configurable for your use case")
        print("  - Registry metadata provides rich context about agent sources")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Note: This might be expected if the registry is not yet populated with agents.")
