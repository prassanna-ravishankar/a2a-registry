"""Seed database from agents/*.json files"""

import asyncio
import json
import os
from pathlib import Path

import asyncpg


async def seed_database():
    """Import agents from JSON files into the database"""

    # Database connection from environment - supports both DATABASE_URL and individual vars
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = os.environ.get("DB_PORT", "5432")
        db_name = os.environ.get("DB_NAME", "a2a_registry")
        db_user = os.environ.get("DB_USER", "postgres")
        db_password = os.environ.get("DB_PASSWORD", "postgres")
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    conn = await asyncpg.connect(database_url)

    try:
        # Get agents directory (relative to backend)
        agents_dir = Path(__file__).parent.parent / "agents"

        if not agents_dir.exists():
            print(f"Agents directory not found: {agents_dir}")
            return

        # Clear existing agents
        await conn.execute("DELETE FROM health_checks")
        await conn.execute("DELETE FROM agent_flags")
        await conn.execute("DELETE FROM agents")
        print("Cleared existing data")

        # Process all JSON files
        json_files = sorted(agents_dir.glob("*.json"))
        print(f"Found {len(json_files)} agent files")

        imported = 0
        errors = []

        for json_file in json_files:
            try:
                with open(json_file) as f:
                    agent = json.load(f)

                # Extract fields with defaults
                protocol_version = agent.get("protocolVersion", "0.3.0")
                name = agent.get("name", "")
                description = agent.get("description", "")
                author = agent.get("author", "")
                well_known_uri = agent.get("wellKnownURI", "")
                url = agent.get("url", "")
                version = agent.get("version", "1.0.0")

                provider = agent.get("provider")
                documentation_url = agent.get("documentationUrl")

                capabilities = agent.get("capabilities", {
                    "streaming": False,
                    "pushNotifications": False,
                    "stateTransitionHistory": False
                })

                default_input_modes = agent.get("defaultInputModes", ["text/plain"])
                default_output_modes = agent.get("defaultOutputModes", ["text/plain"])
                skills = agent.get("skills", [])

                # Conformance: None if not present (standard), False if explicitly false
                conformance = agent.get("conformance")

                # Insert into database
                await conn.execute("""
                    INSERT INTO agents (
                        protocol_version, name, description, author, well_known_uri,
                        url, version, provider, documentation_url, capabilities,
                        default_input_modes, default_output_modes, skills, conformance
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """,
                    protocol_version,
                    name,
                    description,
                    author,
                    well_known_uri,
                    url,
                    version,
                    json.dumps(provider) if provider else None,
                    documentation_url,
                    json.dumps(capabilities),
                    json.dumps(default_input_modes),
                    json.dumps(default_output_modes),
                    json.dumps(skills),
                    conformance,
                )

                imported += 1
                conformance_status = "non-standard" if conformance is False else "standard"
                print(f"  Imported: {name} ({conformance_status})")

            except Exception as e:
                errors.append((json_file.name, str(e)))
                print(f"  Error: {json_file.name} - {e}")

        print(f"\nImported {imported} agents")
        if errors:
            print(f"Errors: {len(errors)}")
            for filename, error in errors:
                print(f"  {filename}: {error}")

        # Show summary
        total = await conn.fetchval("SELECT COUNT(*) FROM agents")
        standard = await conn.fetchval("SELECT COUNT(*) FROM agents WHERE conformance IS NULL OR conformance = true")
        non_standard = await conn.fetchval("SELECT COUNT(*) FROM agents WHERE conformance = false")

        print(f"\nDatabase summary:")
        print(f"  Total agents: {total}")
        print(f"  Standard: {standard}")
        print(f"  Non-standard: {non_standard}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
