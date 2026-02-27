"""
Agent card validation - based on a2a-inspector approach.
https://github.com/a2aproject/a2a-inspector/blob/main/backend/validators.py

When a2a-sdk is installed, AgentCard.model_validate() from the official SDK is
used as the primary validator, keeping us in sync with spec updates automatically.
Falls back to manual validation if the SDK is not available.
"""

# TODO: Once a2a-sdk is a stable transitive dependency everywhere, remove the
#       manual fallback below and import AgentCard unconditionally.

from typing import Any

try:
    from a2a.types import AgentCard as _AgentCard
    from pydantic import ValidationError as _ValidationError

    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SDK_AVAILABLE = False


def validate_agent_card(card_data: dict[str, Any], strict: bool = False) -> list[str]:
    """
    Validate the structure and fields of an agent card.

    When a2a-sdk is installed, delegates to AgentCard.model_validate() from the
    official SDK for primary validation, then applies registry-specific checks
    (e.g. non-empty name/description strings) that the SDK does not enforce.

    Falls back to full manual validation when the SDK is not installed.

    Based on A2A Protocol specification:
    https://a2a-protocol.org/latest/specification/

    Args:
        card_data: The agent card dictionary to validate.  Both camelCase and
                   snake_case field names are accepted (e.g. protocolVersion /
                   protocol_version) because some agent cards follow the SDK's
                   snake_case naming rather than the JSON spec's camelCase.
        strict: If True, require all A2A Protocol fields. If False (default),
                only require core fields for backwards compatibility.

    Returns a list of error strings (empty if valid).
    """
    # Normalise snake_case → camelCase so SDK + manual path both work
    card_data = _normalise_fields(card_data)

    if _SDK_AVAILABLE:
        return _validate_with_sdk(card_data, strict)
    return _validate_manual(card_data, strict)  # pragma: no cover


# ---------------------------------------------------------------------------
# Field normalisation
# ---------------------------------------------------------------------------

_SNAKE_TO_CAMEL: dict[str, str] = {
    "protocol_version": "protocolVersion",
    "default_input_modes": "defaultInputModes",
    "default_output_modes": "defaultOutputModes",
    "documentation_url": "documentationUrl",
    "icon_url": "iconUrl",
    "supports_authenticated_extended_card": "supportsAuthenticatedExtendedCard",
    "security_schemes": "securitySchemes",
    "preferred_transport": "preferredTransport",
    "additional_interfaces": "additionalInterfaces",
}


def _normalise_fields(card: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *card* with snake_case keys promoted to camelCase."""
    result = dict(card)
    for snake, camel in _SNAKE_TO_CAMEL.items():
        if snake in result and camel not in result:
            result[camel] = result.pop(snake)
    return result


# ---------------------------------------------------------------------------
# SDK-backed validation (primary path)
# ---------------------------------------------------------------------------

def _validate_with_sdk(card_data: dict[str, Any], strict: bool) -> list[str]:
    """Validate using AgentCard.model_validate() from a2a-sdk."""
    errors: list[str] = []

    # In non-strict mode the SDK's required fields (capabilities,
    # defaultInputModes, defaultOutputModes, skills) are not enforced.
    # We achieve this by supplying safe defaults before SDK validation so
    # that only the core fields are checked by the SDK.
    data_for_sdk = dict(card_data)
    if not strict:
        data_for_sdk.setdefault("capabilities", {})
        data_for_sdk.setdefault("defaultInputModes", ["text/plain"])
        data_for_sdk.setdefault("defaultOutputModes", ["text/plain"])
        data_for_sdk.setdefault("skills", [])

    try:
        _AgentCard.model_validate(data_for_sdk)
    except _ValidationError as exc:
        for err in exc.errors():
            loc = " -> ".join(str(p) for p in err["loc"]) if err["loc"] else "root"
            errors.append(f"Field '{loc}': {err['msg']}")

    # Registry-specific checks the SDK does not enforce
    errors.extend(_check_non_empty_strings(card_data))
    errors.extend(_check_url_scheme(card_data))
    if "skills" in card_data:
        errors.extend(_validate_skills_extra(card_data["skills"]))

    return errors


# ---------------------------------------------------------------------------
# Shared fine-grained checks used by both paths
# ---------------------------------------------------------------------------

def _check_non_empty_strings(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("name", "description"):
        if field in card:
            val = card[field]
            if not isinstance(val, str) or not val.strip():
                errors.append(f"Field '{field}' must be a non-empty string.")
    return errors


def _check_url_scheme(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("url", "documentationUrl"):
        val = card.get(field)
        if val is None:
            continue
        if not isinstance(val, str):
            errors.append(f"Field '{field}' must be a string.")
        elif not (val.startswith("http://") or val.startswith("https://")):
            errors.append(f"Field '{field}' must be an absolute URL starting with http:// or https://.")
    return errors


def _validate_skills_extra(skills: Any) -> list[str]:
    """Extra per-skill checks beyond what the SDK enforces (non-empty id/name)."""
    errors: list[str] = []
    if not isinstance(skills, list):
        return errors
    for i, skill in enumerate(skills):
        if not isinstance(skill, dict):
            continue
        for field in ("id", "name"):
            if field in skill:
                val = skill[field]
                if not isinstance(val, str) or not val.strip():
                    errors.append(f"Skill at index {i}: '{field}' must be a non-empty string.")
    return errors


# ---------------------------------------------------------------------------
# Manual validation fallback (used when a2a-sdk is not installed)
# ---------------------------------------------------------------------------

def _validate_manual(card_data: dict[str, Any], strict: bool) -> list[str]:  # pragma: no cover
    """Full manual validation - mirrors SDK requirements without importing it."""
    errors: list[str] = []

    core_required = frozenset(["name", "description", "url", "version"])
    extended_required = frozenset(["capabilities", "defaultInputModes", "defaultOutputModes", "skills"])

    required_fields = core_required | extended_required if strict else core_required

    for field in required_fields:
        if field not in card_data:
            errors.append(f"Required field is missing: '{field}'.")

    errors.extend(_check_non_empty_strings(card_data))
    errors.extend(_check_url_scheme(card_data))

    if "version" in card_data:
        if not isinstance(card_data["version"], str):
            errors.append("Field 'version' must be a string.")

    if "capabilities" in card_data:
        if not isinstance(card_data["capabilities"], dict):
            errors.append("Field 'capabilities' must be an object.")

    for new_name, old_name in [("defaultInputModes", "inputModes"), ("defaultOutputModes", "outputModes")]:
        field = new_name if new_name in card_data else old_name if old_name in card_data else None
        if field:
            value = card_data[field]
            if not isinstance(value, list):
                errors.append(f"Field '{field}' must be an array of strings.")
            elif not value:
                errors.append(f"Field '{field}' must not be empty.")
            elif not all(isinstance(item, str) for item in value):
                errors.append(f"All items in '{field}' must be strings.")

    if "skills" in card_data:
        skills = card_data["skills"]
        if not isinstance(skills, list):
            errors.append("Field 'skills' must be an array of AgentSkill objects.")
        elif skills:
            errors.extend(_validate_skills(skills))

    if "provider" in card_data:
        if not isinstance(card_data["provider"], dict):
            errors.append("Field 'provider' must be an object.")

    return errors


def _validate_skills(skills: list[dict[str, Any]]) -> list[str]:
    """Validate the skills array structure (manual path)."""
    errors: list[str] = []
    required_skill_fields = frozenset(["id", "name", "description"])

    for i, skill in enumerate(skills):
        if not isinstance(skill, dict):
            errors.append(f"Skill at index {i} must be an object.")
            continue

        for field in required_skill_fields:
            if field not in skill:
                errors.append(f"Skill at index {i} missing required field: '{field}'.")

        for field in ("id", "name"):
            if field in skill:
                if not isinstance(skill[field], str) or not skill[field].strip():
                    errors.append(f"Skill at index {i}: '{field}' must be a non-empty string.")

        if "tags" in skill:
            tags = skill["tags"]
            if not isinstance(tags, list):
                errors.append(f"Skill at index {i}: 'tags' must be an array.")
            elif not all(isinstance(tag, str) for tag in tags):
                errors.append(f"Skill at index {i}: all tags must be strings.")

        for field in ("inputModes", "outputModes"):
            if field in skill:
                value = skill[field]
                if not isinstance(value, list):
                    errors.append(f"Skill at index {i}: '{field}' must be an array.")
                elif not all(isinstance(item, str) for item in value):
                    errors.append(f"Skill at index {i}: all items in '{field}' must be strings.")

    return errors


# ---------------------------------------------------------------------------
# Well-known URI validation (unchanged)
# ---------------------------------------------------------------------------

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

    if not (uri.startswith("http://") or uri.startswith("https://")):
        errors.append("wellKnownURI must be an absolute URL starting with http:// or https://.")
        return errors

    standard_paths = ("/.well-known/agent.json", "/.well-known/agent-card.json")
    alternative_paths = ("/agent.json", "/agent-card.json")
    valid_paths = standard_paths + alternative_paths

    if not any(uri.endswith(path) for path in valid_paths):
        errors.append(
            "wellKnownURI must end with a valid agent card path: "
            "/.well-known/agent.json or /.well-known/agent-card.json"
        )

    return errors
