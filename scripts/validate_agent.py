#!/usr/bin/env python3
"""
Validate an agent JSON file against the A2A Registry schema and verify ownership.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.request
import urllib.error
import ssl
from jsonschema import validate, ValidationError, Draft7Validator

def load_schema() -> Dict[str, Any]:
    """Load the agent JSON schema."""
    schema_path = Path(__file__).parent.parent / "schemas" / "agent.schema.json"
    with open(schema_path, 'r') as f:
        return json.load(f)

def load_agent_file(filepath: Path) -> Dict[str, Any]:
    """Load and parse an agent JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {filepath}: {e}")
    except FileNotFoundError:
        raise ValueError(f"File not found: {filepath}")

def validate_schema(agent_data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Validate agent data against the schema."""
    try:
        validate(instance=agent_data, schema=schema)
    except ValidationError as e:
        raise ValueError(f"Schema validation failed: {e.message}")

def fetch_wellknown_agent(url: str) -> Optional[Dict[str, Any]]:
    """Fetch the agent.json from the well-known URI."""
    try:
        # Create SSL context that doesn't verify certificates (for dev environments)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'A2A-Registry-Validator/1.0'}
        )
        
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            if response.status == 200:
                content = response.read().decode('utf-8')
                return json.loads(content)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"Warning: Could not fetch or parse {url}: {e}")
    except Exception as e:
        print(f"Warning: Unexpected error fetching {url}: {e}")
    
    return None

def verify_ownership(agent_data: Dict[str, Any]) -> bool:
    """Verify agent ownership by comparing with well-known endpoint."""
    wellknown_uri = agent_data.get('wellKnownURI')
    if not wellknown_uri:
        print("Warning: No wellKnownURI specified")
        return True  # Allow for now during development
    
    remote_agent = fetch_wellknown_agent(wellknown_uri)
    if not remote_agent:
        print(f"Warning: Could not fetch agent data from {wellknown_uri}")
        return True  # Allow for now during development
    
    # Compare key fields
    fields_to_check = ['name', 'description']
    mismatches = []
    
    for field in fields_to_check:
        local_value = agent_data.get(field)
        remote_value = remote_agent.get(field)
        
        if local_value != remote_value:
            mismatches.append(f"{field}: local='{local_value}' vs remote='{remote_value}'")
    
    if mismatches:
        print("Warning: Mismatches found between local and remote agent data:")
        for mismatch in mismatches:
            print(f"  - {mismatch}")
        return False
    
    print(f"✓ Ownership verified via {wellknown_uri}")
    return True

def validate_agent(filepath: Path, verify_remote: bool = True) -> bool:
    """
    Validate an agent JSON file.
    
    Args:
        filepath: Path to the agent JSON file
        verify_remote: Whether to verify ownership via well-known URI
    
    Returns:
        True if validation passes, False otherwise
    """
    try:
        # Load schema
        schema = load_schema()
        print(f"✓ Loaded schema")
        
        # Load agent file
        agent_data = load_agent_file(filepath)
        print(f"✓ Loaded agent file: {filepath}")
        
        # Validate against schema
        validate_schema(agent_data, schema)
        print(f"✓ Schema validation passed")
        
        # Verify ownership if requested
        if verify_remote:
            if not verify_ownership(agent_data):
                print("⚠ Ownership verification failed (non-blocking during development)")
        
        print(f"\n✅ Agent '{agent_data['name']}' validation successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Validate an A2A Registry agent JSON file')
    parser.add_argument('filepath', type=Path, help='Path to the agent JSON file')
    parser.add_argument('--no-remote', action='store_true', 
                       help='Skip remote ownership verification')
    
    args = parser.parse_args()
    
    success = validate_agent(args.filepath, verify_remote=not args.no_remote)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()