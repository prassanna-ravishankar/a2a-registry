#!/usr/bin/env python3
"""
Generate a consolidated registry.json file from all agent JSON files.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone

def load_agent_files(agents_dir: Path) -> List[Dict[str, Any]]:
    """Load all valid agent JSON files from the agents directory."""
    agents = []
    
    # Get all JSON files in the agents directory
    json_files = sorted(agents_dir.glob("*.json"))
    
    for filepath in json_files:
        try:
            with open(filepath, 'r') as f:
                agent_data = json.load(f)
                # Add metadata
                agent_data['_id'] = filepath.stem  # filename without extension
                agent_data['_source'] = f"agents/{filepath.name}"
                agents.append(agent_data)
                print(f"✓ Loaded: {filepath.name}", file=sys.stderr)
        except Exception as e:
            print(f"⚠ Skipping {filepath.name}: {e}", file=sys.stderr)
    
    return agents

def generate_registry(agents_dir: Path) -> Dict[str, Any]:
    """Generate the complete registry object."""
    agents = load_agent_files(agents_dir)
    
    registry = {
        "version": "1.0.0",
        "generated": datetime.now(timezone.utc).isoformat(),
        "count": len(agents),
        "agents": agents
    }
    
    print(f"\n✅ Generated registry with {len(agents)} agents", file=sys.stderr)
    return registry

def main():
    parser = argparse.ArgumentParser(description='Generate registry.json from agent files')
    parser.add_argument('agents_dir', type=Path, nargs='?', default='agents',
                       help='Path to the agents directory (default: agents)')
    parser.add_argument('--output', '-o', type=Path,
                       help='Output file path (default: stdout)')
    parser.add_argument('--pretty', action='store_true',
                       help='Pretty-print the JSON output')
    
    args = parser.parse_args()
    
    if not args.agents_dir.exists():
        print(f"Error: Directory not found: {args.agents_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Generate the registry
    registry = generate_registry(args.agents_dir)
    
    # Output the registry
    json_str = json.dumps(registry, indent=2 if args.pretty else None, sort_keys=True)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_str)
        print(f"✅ Written to: {args.output}", file=sys.stderr)
    else:
        print(json_str)

if __name__ == '__main__':
    main()