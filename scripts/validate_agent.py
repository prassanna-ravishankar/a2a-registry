#!/usr/bin/env python3
"""
Validate an agent JSON file against both A2A Protocol and Registry requirements.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import urllib.request
import urllib.error
import ssl
import time
import gzip
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
    
    def validate_registry_requirements(self, agent_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
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
            allowed_suffixes = ("/.well-known/agent.json", "/.well-known/agent-card.json")
            if not any(uri.endswith(suffix) for suffix in allowed_suffixes):
                errors.append("wellKnownURI must end with '/.well-known/agent.json' or '/.well-known/agent-card.json'")
        
        return errors, warnings
    
    def verify_ownership(self, agent_data: Dict[str, Any], verify_ssl: bool = True, 
                        max_retries: int = 3, base_delay: float = 1.0) -> Tuple[bool, str]:
        """
        Verify agent ownership via well-known endpoint with robust error handling and retries.
        
        Args:
            agent_data: The agent data to verify
            verify_ssl: Whether to verify SSL certificates (default: True for security)
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay between retries in seconds (default: 1.0)
        """
        wellknown_uri = agent_data.get('wellKnownURI')
        if not wellknown_uri:
            return True, "No wellKnownURI to verify"
        
        # Rate limiting: small delay to be respectful to agent providers
        time.sleep(0.1)
        
        for attempt in range(max_retries + 1):
            try:
                # Create SSL context with proper verification (secure by default)
                ctx = ssl.create_default_context()
                if not verify_ssl:
                    # Only disable SSL verification if explicitly requested (dev/testing)
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                
                req = urllib.request.Request(
                    wellknown_uri,
                    headers={
                        'User-Agent': 'A2A-Registry-Validator/2.0',
                        'Accept': 'application/json',
                        'Accept-Encoding': 'gzip, deflate'
                    }
                )
                
                with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                    if response.status == 200:
                        # Read the raw response data
                        raw_data = response.read()
                        
                        # Check if the response is gzip-compressed
                        if response.headers.get('Content-Encoding') == 'gzip':
                            # Decompress gzip data
                            raw_data = gzip.decompress(raw_data)
                        
                        # Decode to UTF-8
                        content = raw_data.decode('utf-8')
                        
                        try:
                            remote_agent = json.loads(content)
                        except json.JSONDecodeError as json_err:
                            return False, f"Invalid JSON in well-known endpoint: {json_err}"
                        
                        # Compare key fields
                        mismatches = []
                        for field in ['name', 'description']:
                            local_val = agent_data.get(field)
                            remote_val = remote_agent.get(field)
                            if local_val != remote_val:
                                mismatches.append(f"{field}: local='{local_val}' vs remote='{remote_val}'")
                        
                        if mismatches:
                            return False, f"Field mismatches found:\n  " + "\n  ".join(mismatches)
                        return True, "Ownership verified successfully"
                    else:
                        return False, f"Well-known endpoint returned HTTP {response.status}"
                        
            except urllib.error.HTTPError as e:
                error_msg = self._format_http_error(e, wellknown_uri, attempt, max_retries)
                if attempt == max_retries:
                    return False, error_msg
                # Retry on 5xx errors (server issues) but not 4xx (client errors)
                if e.code >= 500:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(delay)
                    continue
                else:
                    return False, error_msg
                    
            except urllib.error.URLError as e:
                error_msg = self._format_url_error(e, wellknown_uri, attempt, max_retries)
                if attempt == max_retries:
                    return False, error_msg
                # Retry on network issues
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                time.sleep(delay)
                continue
                
            except ssl.SSLError as e:
                return False, f"SSL verification failed for {wellknown_uri}: {e}. " + \
                              "If this is a development/testing environment, use --no-ssl-verify flag."
                              
            except TimeoutError:
                error_msg = f"Timeout connecting to {wellknown_uri}"
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(delay)
                    continue
                return False, f"{error_msg} (after {max_retries + 1} attempts)"
                
            except Exception as e:
                # Catch-all for unexpected errors
                return False, f"Unexpected error accessing {wellknown_uri}: {type(e).__name__}: {e}"
        
        return False, f"Failed to verify after {max_retries + 1} attempts"
    
    def _format_http_error(self, error: urllib.error.HTTPError, uri: str, attempt: int, max_attempts: int) -> str:
        """Format HTTP error with helpful context."""
        retry_info = f" (attempt {attempt + 1}/{max_attempts + 1})" if max_attempts > 0 else ""
        
        if error.code == 404:
            return f"Well-known endpoint not found (404): {uri}{retry_info}. " + \
                   "Ensure your agent publishes /.well-known/agent.json or /.well-known/agent-card.json"
        elif error.code == 403:
            return f"Access forbidden (403): {uri}{retry_info}. Check endpoint permissions."
        elif error.code >= 500:
            return f"Server error ({error.code}): {uri}{retry_info}. Will retry if attempts remaining."
        else:
            return f"HTTP error ({error.code}): {uri}{retry_info}"
    
    def _format_url_error(self, error: urllib.error.URLError, uri: str, attempt: int, max_attempts: int) -> str:
        """Format URL error with helpful context."""
        retry_info = f" (attempt {attempt + 1}/{max_attempts + 1})" if max_attempts > 0 else ""
        
        if "Name or service not known" in str(error.reason):
            return f"Domain not found: {uri}{retry_info}. Check if the domain exists and is accessible."
        elif "Connection refused" in str(error.reason):
            return f"Connection refused: {uri}{retry_info}. Server may be down or blocking requests."
        elif "timed out" in str(error.reason):
            return f"Connection timeout: {uri}{retry_info}. Network may be slow or server unresponsive."
        else:
            return f"Network error: {uri}{retry_info}. {error.reason}"
    
    def validate(self, filepath: Path, verify_remote: bool = True, verify_ssl: bool = True,
                max_retries: int = 3) -> Dict[str, Any]:
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
                verified, message = self.verify_ownership(agent_data, verify_ssl=verify_ssl, max_retries=max_retries)
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
        description='Validate an A2A Registry agent against Protocol and Registry requirements',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Security Options:
  SSL verification is enabled by default for production security.
  Use --no-ssl-verify only for development/testing with self-signed certificates.
  
  Network retries help handle transient failures but respect rate limits.
  The validator includes automatic delays to be respectful to agent providers.

Examples:
  %(prog)s agents/my-agent.json                    # Standard validation
  %(prog)s agents/my-agent.json --no-remote        # Skip ownership check  
  %(prog)s agents/my-agent.json --no-ssl-verify    # Dev/testing mode
  %(prog)s agents/my-agent.json --max-retries 1    # Faster but less reliable
  %(prog)s agents/my-agent.json --json             # JSON output for CI
        """
    )
    parser.add_argument('filepath', type=Path, help='Path to the agent JSON file')
    parser.add_argument('--no-remote', action='store_true', 
                       help='Skip remote ownership verification')
    parser.add_argument('--no-ssl-verify', action='store_true',
                       help='Disable SSL certificate verification (dev/testing only)')
    parser.add_argument('--max-retries', type=int, default=3, metavar='N',
                       help='Maximum retry attempts for network requests (default: 3)')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.max_retries < 0:
        parser.error("--max-retries must be non-negative")
    
    if args.no_ssl_verify:
        print("⚠️  SSL verification disabled - use only for development/testing!", file=sys.stderr)
    
    validator = AgentValidator()
    result = validator.validate(
        args.filepath, 
        verify_remote=not args.no_remote,
        verify_ssl=not args.no_ssl_verify,
        max_retries=args.max_retries
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_validation_result(result, args.filepath)
    
    sys.exit(0 if result["valid"] else 1)

if __name__ == '__main__':
    main()