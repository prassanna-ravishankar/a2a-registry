#!/usr/bin/env python3
"""
Validate that Agent.async_connect() works end-to-end with live registry agents.

Uses the modernized ClientFactory.connect() under the hood.

Usage:
    cd client-python
    uv run --extra all python examples/validate_async_connect.py
"""

import asyncio

from a2a.client.helpers import create_text_message_object
from a2a.types import Message, Task

from a2a_registry import AsyncAPIRegistry


def extract_text(event) -> str:
    if isinstance(event, tuple):
        task = event[0]
        for artifact in task.artifacts or []:
            for part in artifact.parts or []:
                text = getattr(part.root, "text", None)
                if text:
                    return text
        if task.status and task.status.message:
            for part in task.status.message.parts or []:
                text = getattr(part.root, "text", None)
                if text:
                    return text
        return f"(task {task.status.state}, no text)"
    elif isinstance(event, Message):
        for part in event.parts or []:
            text = getattr(part.root, "text", None)
            if text:
                return text
        return "(message, no text)"
    return f"({type(event).__name__})"


async def main():
    async with AsyncAPIRegistry() as registry:
        agents = await registry.get_all()
        targets = [
            a for a in agents
            if a.is_healthy and a.conformance is True and (a.uptime_percentage or 0) > 90
        ]
        print(f"Found {len(targets)} healthy conformant agents\n")

        successes = 0
        failures = 0

        for agent in targets:
            print(f"--- {agent.name} ---")
            print(f"  URI: {agent.wellKnownURI}")
            try:
                client = await agent.async_connect()
                print(f"  Connected OK")

                message = create_text_message_object(content="Hello, what can you do?")
                async for event in client.send_message(message):
                    text = extract_text(event)
                    print(f"  Response: {text[:200]}")
                    break

                successes += 1
            except Exception as e:
                print(f"  FAILED: {type(e).__name__}: {e}")
                failures += 1
            print()

        print(f"Results: {successes} succeeded, {failures} failed out of {len(targets)} agents")


if __name__ == "__main__":
    asyncio.run(main())
