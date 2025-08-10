#!/usr/bin/env python3
"""
Validate an agent JSON file against both A2A Protocol and Registry requirements.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error
import ssl
from jsonschema import validate, ValidationError, Draft7Validator

class AgentValidator:
    """Validates agent entries against A2A Protocol and Registry requirements."""
    
    def __init__(self):
        self.a2a_schema = self._load_a2a_schema()
        self.registry_requirements = self._load_registry_requirements()
    
    def _load_a2a_schema(self) -> Dict[str, Any]:
        """Load the official A2A AgentCard schema."""
        schema_path = Path(__file__).parent.parent / "schemas" / "a2a-official.schema.json"
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        # Return the full schema with definitions so $ref works
        return schema
    
    def _load_registry_requirements(self) -> Dict[str, List[str]]:
        """Define registry-specific requirements."""
        return {
            "required_fields": ["author", "wellKnownURI"],
            "recommended_fields": ["homepage", "repository", "license", "pricing", "contact"]
        }
    
    def validate_a2a_compliance(self, agent_data: Dict[str, Any]) -> List[str]:
        """Validate against A2A Protocol requirements."""
        errors = []
        
        # Check required A2A fields
        required_a2a = [
            "protocolVersion", "name", "description", "url", "version",
            "capabilities", "skills", "defaultInputModes", "defaultOutputModes"
        ]
        
        for field in required_a2a:
            if field not in agent_data:
                errors.append(f"Missing required A2A field: {field}")
        
        # Validate skills structure
        if "skills" in agent_data:
            for i, skill in enumerate(agent_data["skills"]):
                required_skill_fields = ["id", "name", "description", "tags"]
                for field in required_skill_fields:
                    if field not in skill:
                        errors.append(f"Skill {i} missing required field: {field}")
        
        # Validate against schema (use the AgentCard definition)
        try:
            # Create a schema that references the AgentCard definition
            agent_card_schema = {
                "$ref": "#/definitions/AgentCard",
                "definitions": self.a2a_schema.get("definitions", {})
            }
            validate(instance=agent_data, schema=agent_card_schema)
        except ValidationError as e:
            errors.append(f"A2A Schema validation: {e.message}")
        
        return errors
    
    def validate_registry_requirements(self, agent_data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate registry-specific requirements."""
        errors = []
        warnings = []
        
        # Check required registry fields
        for field in self.registry_requirements["required_fields"]:
            if field not in agent_data:
                errors.append(f"Missing required registry field: {field}")
        
        # Check recommended fields
        for field in self.registry_requirements["recommended_fields"]:
            if field not in agent_data:
                warnings.append(f"Missing recommended field: {field}")
        
        # Validate wellKnownURI format
        if "wellKnownURI" in agent_data:
            uri = agent_data["wellKnownURI"]
            if not uri.endswith("/.well-known/agent.json"):
                errors.append("wellKnownURI must end with '/.well-known/agent.json'")
        
        return errors, warnings
    
    def verify_ownership(self, agent_data: Dict[str, Any]) -> tuple[bool, str]:
        """Verify agent ownership via well-known endpoint."""
        wellknown_uri = agent_data.get('wellKnownURI')
        if not wellknown_uri:
            return True, "No wellKnownURI to verify"
        
        try:
            # Create SSL context that doesn't verify certificates (for dev)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(
                wellknown_uri,
                headers={'User-Agent': 'A2A-Registry-Validator/2.0'}
            )
            
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                if response.status == 200:
                    content = response.read().decode('utf-8')
                    remote_agent = json.loads(content)
                    
                    # Compare key fields
                    mismatches = []
                    for field in ['name', 'description']:
                        if agent_data.get(field) != remote_agent.get(field):
                            mismatches.append(field)
                    
                    if mismatches:
                        return False, f"Mismatches in fields: {', '.join(mismatches)}"
                    return True, "Ownership verified"
                    
        except Exception as e:
            return False, f"Could not verify: {str(e)}"
    
    def validate(self, filepath: Path, verify_remote: bool = True) -> Dict[str, Any]:
        """
        Perform complete validation of an agent file.
        
        Returns a dict with:
        - valid: bool
        - a2a_errors: List[str]
        - registry_errors: List[str]
        - warnings: List[str]
        - ownership_verified: bool
        - ownership_message: str
        """
        result = {
            "valid": False,
            "a2a_errors": [],
            "registry_errors": [],
            "warnings": [],
            "ownership_verified": False,
            "ownership_message": ""
        }
        
        try:
            # Load agent file
            with open(filepath, 'r') as f:
                agent_data = json.load(f)
            
            # Validate A2A compliance
            result["a2a_errors"] = self.validate_a2a_compliance(agent_data)
            
            # Validate registry requirements
            reg_errors, reg_warnings = self.validate_registry_requirements(agent_data)
            result["registry_errors"] = reg_errors
            result["warnings"] = reg_warnings
            
            # Verify ownership if requested
            if verify_remote:
                verified, message = self.verify_ownership(agent_data)
                result["ownership_verified"] = verified
                result["ownership_message"] = message
            
            # Determine overall validity
            result["valid"] = len(result["a2a_errors"]) == 0 and len(result["registry_errors"]) == 0
            
        except json.JSONDecodeError as e:
            result["registry_errors"].append(f"Invalid JSON: {e}")
        except FileNotFoundError:
            result["registry_errors"].append(f"File not found: {filepath}")
        except Exception as e:
            result["registry_errors"].append(f"Unexpected error: {e}")
        
        return result

def print_validation_result(result: Dict[str, Any], filepath: Path) -> None:
    """Pretty print validation results."""
    print(f"\n{'='*60}")
    print(f"Validation Report for: {filepath.name}")
    print(f"{'='*60}")
    
    if result["valid"]:
        print("✅ VALID - Agent passes all requirements")
    else:
        print("❌ INVALID - Agent has validation errors")
    
    print(f"\nA2A Protocol Compliance:")
    if result["a2a_errors"]:
        for error in result["a2a_errors"]:
            print(f"  ❌ {error}")
    else:
        print("  ✅ Fully compliant with A2A Protocol")
    
    print(f"\nRegistry Requirements:")
    if result["registry_errors"]:
        for error in result["registry_errors"]:
            print(f"  ❌ {error}")
    else:
        print("  ✅ Meets all registry requirements")
    
    if result["warnings"]:
        print(f"\n⚠️  Warnings (non-blocking):")
        for warning in result["warnings"]:
            print(f"  - {warning}")
    
    print(f"\nOwnership Verification:")
    if result["ownership_verified"]:
        print(f"  ✅ {result['ownership_message']}")
    else:
        print(f"  ⚠️  {result['ownership_message']}")
    
    print(f"{'='*60}\n")

def main():
    parser = argparse.ArgumentParser(
        description='Validate an A2A Registry agent against Protocol and Registry requirements'
    )
    parser.add_argument('filepath', type=Path, help='Path to the agent JSON file')
    parser.add_argument('--no-remote', action='store_true', 
                       help='Skip remote ownership verification')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')
    
    args = parser.parse_args()
    
    validator = AgentValidator()
    result = validator.validate(args.filepath, verify_remote=not args.no_remote)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_validation_result(result, args.filepath)
    
    sys.exit(0 if result["valid"] else 1)

if __name__ == '__main__':
    main()