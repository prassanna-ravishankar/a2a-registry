#!/usr/bin/env python3
"""
Test suite for agent validation to ensure invalid agents are properly rejected.
"""

import json
import sys
from pathlib import Path
import tempfile

# Add parent directory to path to import validate_agent
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.validate_agent import AgentValidator


def test_invalid_agents():
    """Test that invalid agents fail validation appropriately."""

    # Load test cases
    test_cases_file = Path(__file__).parent / "test_invalid_agents.json"
    with open(test_cases_file) as f:
        test_data = json.load(f)

    validator = AgentValidator()
    passed = 0
    failed = 0

    for test_case in test_data["test_cases"]:
        test_name = test_case["name"]
        agent_data = test_case["agent"]
        expected_errors = test_case["expected_errors"]

        # Write agent to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(agent_data, f)
            temp_file = Path(f.name)

        try:
            # Validate the agent
            result = validator.validate(temp_file, verify_remote=False)

            # Check that validation failed
            if result["valid"]:
                print(f"❌ FAIL: {test_name}")
                print(f"   Expected validation to fail, but it passed")
                failed += 1
                continue

            # Check that expected errors are present
            all_errors = result["a2a_errors"] + result["registry_errors"]
            missing_errors = []

            for expected_error in expected_errors:
                found = any(expected_error in error for error in all_errors)
                if not found:
                    missing_errors.append(expected_error)

            if missing_errors:
                print(f"❌ FAIL: {test_name}")
                print(f"   Missing expected errors:")
                for error in missing_errors:
                    print(f"     - {error}")
                print(f"   Actual errors:")
                for error in all_errors:
                    print(f"     - {error}")
                failed += 1
            else:
                print(f"✅ PASS: {test_name}")
                passed += 1

        finally:
            temp_file.unlink()

    print(f"\n{'='*60}")
    print(f"Test Results")
    print(f"{'='*60}")
    print(f"Total: {passed + failed}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"{'='*60}\n")

    return failed == 0


if __name__ == "__main__":
    success = test_invalid_agents()
    sys.exit(0 if success else 1)
