#!/usr/bin/env python3
"""
Migrate existing agents from JSON files to the database.

One-time migration script to sync the 103 existing agents from /agents/*.json
into the new PostgreSQL database.
"""

import asyncio
import json
import sys
from pathlib import Path

import asyncpg

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import settings
from app.repositories import AgentRepository
from app.database import Database


async def migrate_agents():
    """Migrate all agents from JSON files to database"""

    # Connect to database
    db = Database()
    await db.connect()
    print("✅ Database connected")

    agent_repo = AgentRepository(db)
    agents_dir = Path(__file__).parent.parent / "agents"

    if not agents_dir.exists():
        print(f"❌ Agents directory not found: {agents_dir}")
        return

    json_files = sorted(agents_dir.glob("*.json"))
    print(f"\n📂 Found {len(json_files)} agent JSON files")

    success_count = 0
    skip_count = 0
    error_count = 0

    for filepath in json_files:
        try:
            with open(filepath, "r") as f:
                agent_data = json.load(f)

            agent_name = agent_data.get("name", filepath.stem)
            well_known_uri = agent_data.get("wellKnownURI")

            # Check if already exists
            existing = await agent_repo.get_by_well_known_uri(well_known_uri)
            if existing:
                print(f"⏭️  Skipping (already exists): {agent_name}")
                skip_count += 1
                continue

            # Prepare data for insertion
            # Convert camelCase to snake_case for database
            insert_data = {
                "protocol_version": agent_data.get("protocolVersion", "0.3.0"),
                "name": agent_data["name"],
                "description": agent_data["description"],
                "author": agent_data["author"],
                "well_known_uri": well_known_uri,
                "url": agent_data["url"],
                "version": agent_data["version"],
                "provider": json.dumps(agent_data.get("provider")),
                "documentation_url": agent_data.get("documentationUrl"),
                "capabilities": json.dumps(agent_data["capabilities"]),
                "default_input_modes": json.dumps(agent_data["defaultInputModes"]),
                "default_output_modes": json.dumps(agent_data["defaultOutputModes"]),
                "skills": json.dumps(agent_data["skills"]),
            }

            # Insert into database
            query = """
                INSERT INTO agents (
                    protocol_version, name, description, author, well_known_uri,
                    url, version, provider, documentation_url, capabilities,
                    default_input_modes, default_output_modes, skills
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING id
            """

            agent_id = await db.fetchval(
                query,
                insert_data["protocol_version"],
                insert_data["name"],
                insert_data["description"],
                insert_data["author"],
                insert_data["well_known_uri"],
                insert_data["url"],
                insert_data["version"],
                insert_data["provider"],
                insert_data["documentation_url"],
                insert_data["capabilities"],
                insert_data["default_input_modes"],
                insert_data["default_output_modes"],
                insert_data["skills"],
            )

            print(f"✅ Migrated: {agent_name} (ID: {agent_id})")
            success_count += 1

        except Exception as e:
            print(f"❌ Error migrating {filepath.name}: {e}")
            error_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Migration Summary")
    print(f"{'='*60}")
    print(f"✅ Successfully migrated: {success_count}")
    print(f"⏭️  Skipped (already exist): {skip_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total processed: {len(json_files)}")
    print(f"{'='*60}\n")

    # Disconnect
    await db.disconnect()
    print("👋 Database disconnected")


if __name__ == "__main__":
    print("🚀 A2A Registry Migration Script")
    print("=" * 60)
    print(f"Database: {settings.database_url}")
    print("=" * 60)
    print()

    asyncio.run(migrate_agents())
