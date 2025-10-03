#!/usr/bin/env python3
"""
Demo: Complete A2A Registry → A2A SDK Integration

This demonstrates the full workflow:
1. Discover agent from A2A Registry
2. Connect using agent.async_connect() to get A2A SDK client
3. Send message and receive response

Requirements:
    pip install 'a2a-registry-client[a2a]'

Usage:
    python demo_a2a_integration.py
"""

import sys
import asyncio
sys.path.insert(0, '../src')

from a2a_registry import Registry

async def main():
    print("=" * 70)
    print("A2A WORKFLOW TEST - With Polling")
    print("=" * 70)
    print()

    # Discover and connect
    print("Step 1: Discovering and connecting...")
    registry = Registry()
    agent = registry.search("research")[0]
    client = await agent.async_connect()
    print(f"✓ Connected to: {agent.name}")
    print()

    # Send message
    print("Step 2: Sending message...")
    from a2a.types import Message, TextPart, Role, TaskQueryParams
    import uuid

    message = Message(
        messageId=str(uuid.uuid4()),
        role=Role.user,
        parts=[TextPart(text="What is artificial intelligence?")]
    )

    print("→ USER: What is artificial intelligence?")

    # Get task ID from first response
    task_id = None
    async for item in client.send_message(message):
        if isinstance(item, tuple) and len(item) >= 1:
            task = item[0]
            task_id = task.id
            print(f"  Task submitted: {task_id}")
            print(f"  Task state: {task.status.state}")
            break

    if not task_id:
        print("✗ Failed to get task ID")
        return

    # Poll for completion
    print()
    print("Step 3: Polling for response...")
    max_attempts = 10
    for attempt in range(max_attempts):
        await asyncio.sleep(2)  # Wait 2 seconds between polls

        try:
            # Use TaskQueryParams
            params = TaskQueryParams(id=task_id)
            task_result = await client.get_task(params)

            print(f"  Attempt {attempt + 1}: {task_result.status.state}")

            # Check for completion
            if task_result.status.state.value in ['completed', 'failed']:
                print()
                if task_result.status.state.value == 'completed':
                    # Extract response
                    print("← AGENT: ", end="")
                    if hasattr(task_result, 'history') and task_result.history:
                        for msg in task_result.history:
                            if hasattr(msg, 'role') and msg.role.value == 'agent':
                                for part in msg.parts:
                                    if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                        print(part.root.text)
                    print()
                    print("=" * 70)
                    print("✅ SUCCESS!")
                    print("=" * 70)
                else:
                    print(f"Task failed: {task_result.status.message}")
                break
        except Exception as e:
            print(f"  Poll error: {e}")
            break
    else:
        print()
        print("⚠️  Task didn't complete within timeout")

if __name__ == "__main__":
    asyncio.run(main())
