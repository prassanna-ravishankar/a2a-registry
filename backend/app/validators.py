"""
Agent card validation - based on a2a-inspector approach.
https://github.com/a2aproject/a2a-inspector/blob/main/backend/validators.py
"""

from typing import Any


def validate_agent_card(card_data: dict[str, Any], strict: bool = False) -> list[str]:
    """
    Validate the structure and fields of an agent card.

    Based on A2A Protocol specification:
    https://a2a-protocol.org/latest/specification/

    Args:
        card_data: The agent card dictionary to validate
        strict: If True, require all A2A Protocol fields. If False (default),
                only require core fields for backwards compatibility.

    Returns a list of error strings (empty if valid).
    """
    errors: list[str] = []

    # Core required fields (always required)
    core_required = frozenset([
        "name",
        "description",
        "url",
        "version",
    ])

    # Extended required fields (only in strict mode)
    extended_required = frozenset([
        "capabilities",
        "defaultInputModes",
        "defaultOutputModes",
        "skills",
    ])

    required_fields = core_required | extended_required if strict else core_required

    # Check for presence of all required fields
    for field in required_fields:
        if field not in card_data:
            errors.append(f"Required field is missing: '{field}'.")

    # Validate 'name' is non-empty string
    if "name" in card_data:
        if not isinstance(card_data["name"], str) or not card_data["name"].strip():
            errors.append("Field 'name' must be a non-empty string.")

    # Validate 'description' is non-empty string
    if "description" in card_data:
        if not isinstance(card_data["description"], str) or not card_data["description"].strip():
            errors.append("Field 'description' must be a non-empty string.")

    # Validate 'url' is an absolute URL
    if "url" in card_data:
        url = card_data["url"]
        if not isinstance(url, str):
            errors.append("Field 'url' must be a string.")
        elif not (url.startswith("http://") or url.startswith("https://")):
            errors.append("Field 'url' must be an absolute URL starting with http:// or https://.")

    # Validate 'version' is a string
    if "version" in card_data:
        if not isinstance(card_data["version"], str):
            errors.append("Field 'version' must be a string.")

    # Validate 'capabilities' is a dictionary
    if "capabilities" in card_data:
        if not isinstance(card_data["capabilities"], dict):
            errors.append("Field 'capabilities' must be an object.")

    # Validate input/output modes (support both old and new field names)
    # Old: inputModes, outputModes
    # New: defaultInputModes, defaultOutputModes
    mode_fields = [
        ("defaultInputModes", "inputModes"),
        ("defaultOutputModes", "outputModes"),
    ]
    for new_name, old_name in mode_fields:
        # Check new name first, fall back to old name
        field = new_name if new_name in card_data else old_name if old_name in card_data else None
        if field and field in card_data:
            value = card_data[field]
            if not isinstance(value, list):
                errors.append(f"Field '{field}' must be an array of strings.")
            elif not value:
                errors.append(f"Field '{field}' must not be empty.")
            elif not all(isinstance(item, str) for item in value):
                errors.append(f"All items in '{field}' must be strings.")

    # Validate 'skills' array (if present)
    if "skills" in card_data:
        skills = card_data["skills"]
        if not isinstance(skills, list):
            errors.append("Field 'skills' must be an array of AgentSkill objects.")
        elif skills:  # Only validate if non-empty (empty skills is allowed)
            skill_errors = _validate_skills(skills)
            errors.extend(skill_errors)

    # Validate optional 'provider' object
    if "provider" in card_data:
        provider = card_data["provider"]
        if not isinstance(provider, dict):
            errors.append("Field 'provider' must be an object.")

    # Validate optional 'documentationUrl'
    if "documentationUrl" in card_data:
        doc_url = card_data["documentationUrl"]
        if doc_url is not None:
            if not isinstance(doc_url, str):
                errors.append("Field 'documentationUrl' must be a string.")
            elif not (doc_url.startswith("http://") or doc_url.startswith("https://")):
                errors.append("Field 'documentationUrl' must be an absolute URL.")

    return errors


def _validate_skills(skills: list[dict[str, Any]]) -> list[str]:
    """Validate the skills array structure."""
    errors: list[str] = []

    required_skill_fields = frozenset(["id", "name", "description"])

    for i, skill in enumerate(skills):
        if not isinstance(skill, dict):
            errors.append(f"Skill at index {i} must be an object.")
            continue

        # Check required skill fields
        for field in required_skill_fields:
            if field not in skill:
                errors.append(f"Skill at index {i} missing required field: '{field}'.")

        # Validate skill 'id' is a non-empty string
        if "id" in skill:
            if not isinstance(skill["id"], str) or not skill["id"].strip():
                errors.append(f"Skill at index {i}: 'id' must be a non-empty string.")

        # Validate skill 'name' is a non-empty string
        if "name" in skill:
            if not isinstance(skill["name"], str) or not skill["name"].strip():
                errors.append(f"Skill at index {i}: 'name' must be a non-empty string.")

        # Validate skill 'tags' if present
        if "tags" in skill:
            tags = skill["tags"]
            if not isinstance(tags, list):
                errors.append(f"Skill at index {i}: 'tags' must be an array.")
            elif not all(isinstance(tag, str) for tag in tags):
                errors.append(f"Skill at index {i}: all tags must be strings.")

        # Validate skill input/output modes if present
        for field in ["inputModes", "outputModes"]:
            if field in skill:
                value = skill[field]
                if not isinstance(value, list):
                    errors.append(f"Skill at index {i}: '{field}' must be an array.")
                elif not all(isinstance(item, str) for item in value):
                    errors.append(f"Skill at index {i}: all items in '{field}' must be strings.")

    return errors


def validate_well_known_uri(uri: str) -> list[str]:
    """
    Validate that a wellKnownURI has the correct format.

    Standard paths per A2A Protocol:
    - /.well-known/agent.json
    - /.well-known/agent-card.json

    Returns a list of error strings (empty if valid).
    """
    errors: list[str] = []

    if not uri:
        errors.append("wellKnownURI is required.")
        return errors

    if not isinstance(uri, str):
        errors.append("wellKnownURI must be a string.")
        return errors

    # Must be absolute URL
    if not (uri.startswith("http://") or uri.startswith("https://")):
        errors.append("wellKnownURI must be an absolute URL starting with http:// or https://.")
        return errors

    # Check for valid agent card paths
    standard_paths = ("/.well-known/agent.json", "/.well-known/agent-card.json")
    alternative_paths = ("/agent.json", "/agent-card.json")
    valid_paths = standard_paths + alternative_paths

    if not any(uri.endswith(path) for path in valid_paths):
        errors.append(
            "wellKnownURI must end with a valid agent card path: "
            "/.well-known/agent.json or /.well-known/agent-card.json"
        )

    # Warn about non-standard paths (not an error, just info)
    # This is handled at a higher level if needed

    return errors
