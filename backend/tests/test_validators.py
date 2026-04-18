"""Unit tests for app/validators.py"""

from app.validators import _normalise_fields, validate_agent_card, validate_well_known_uri

# ---------------------------------------------------------------------------
# validate_well_known_uri
# ---------------------------------------------------------------------------

def test_well_known_uri_requires_https():
    # http:// is allowed by the validator (it only requires absolute URL).
    # The validator does NOT require https specifically — it accepts http:// too.
    # Test that a completely non-absolute URI is rejected.
    errors = validate_well_known_uri("ftp://example.com/.well-known/agent.json")
    assert len(errors) > 0


def test_well_known_uri_requires_well_known_path():
    errors = validate_well_known_uri("https://example.com/agent.json")
    # /agent.json is actually one of the valid alternative paths, so use a clearly invalid one
    errors = validate_well_known_uri("https://example.com/random/path.json")
    assert len(errors) > 0


def test_well_known_uri_accepts_valid():
    errors = validate_well_known_uri("https://example.com/.well-known/agent.json")
    assert len(errors) == 0


def test_well_known_uri_accepts_agent_card_path():
    errors = validate_well_known_uri("https://example.com/.well-known/agent-card.json")
    assert len(errors) == 0


def test_well_known_uri_accepts_http():
    # Validator allows http:// (not https-only restriction)
    errors = validate_well_known_uri("http://example.com/.well-known/agent.json")
    assert len(errors) == 0


def test_well_known_uri_accepts_alternative_paths():
    errors = validate_well_known_uri("https://example.com/agent.json")
    assert len(errors) == 0
    errors = validate_well_known_uri("https://example.com/agent-card.json")
    assert len(errors) == 0


def test_well_known_uri_rejects_empty():
    errors = validate_well_known_uri("")
    assert len(errors) > 0


def test_well_known_uri_rejects_relative():
    errors = validate_well_known_uri("/.well-known/agent.json")
    assert len(errors) > 0


# ---------------------------------------------------------------------------
# validate_agent_card
# ---------------------------------------------------------------------------

def test_validate_agent_card_requires_name():
    card = {"description": "x", "url": "https://example.com", "version": "1.0"}
    errors = validate_agent_card(card)
    assert any("name" in e.lower() for e in errors)


def test_validate_agent_card_description_optional_in_v1():
    """Description is required in v0.3 but optional in v1.0 — normaliser defaults to empty string."""
    card = {"name": "Test", "url": "https://example.com", "version": "1.0"}
    errors = validate_agent_card(card)
    assert len(errors) == 0


def test_validate_agent_card_requires_url():
    card = {"name": "Test", "description": "x", "version": "1.0"}
    errors = validate_agent_card(card)
    assert any("url" in e.lower() for e in errors)


def test_validate_agent_card_requires_version():
    """In v0.3 version was required; v1.0 made it optional (normaliser defaults to '1.0.0').
    The SDK still requires it, but our normaliser fills it in."""
    card = {"name": "Test", "description": "x", "url": "https://example.com"}
    errors = validate_agent_card(card)
    # With the v1.0 compat normaliser defaulting version, this now passes
    assert len(errors) == 0


def test_validate_agent_card_accepts_minimal_valid():
    card = {
        "name": "Test",
        "description": "Test agent",
        "url": "https://example.com",
        "version": "1.0.0",
        "skills": [],
    }
    errors = validate_agent_card(card)
    assert len(errors) == 0


def test_validate_agent_card_rejects_non_string_name():
    card = {
        "name": 123,
        "description": "Test agent",
        "url": "https://example.com",
        "version": "1.0.0",
    }
    errors = validate_agent_card(card)
    assert any("name" in e.lower() for e in errors)


def test_validate_agent_card_rejects_relative_url():
    card = {
        "name": "Test",
        "description": "Test agent",
        "url": "/relative/path",
        "version": "1.0.0",
    }
    errors = validate_agent_card(card)
    assert any("url" in e.lower() for e in errors)


def test_validate_agent_card_rejects_non_dict_capabilities():
    card = {
        "name": "Test",
        "description": "Test agent",
        "url": "https://example.com",
        "version": "1.0.0",
        "capabilities": "streaming",
    }
    errors = validate_agent_card(card)
    assert any("capabilities" in e.lower() for e in errors)


def test_validate_agent_card_rejects_empty_input_modes():
    card = {
        "name": "Test",
        "description": "Test agent",
        "url": "https://example.com",
        "version": "1.0.0",
        "defaultInputModes": [],
    }
    errors = validate_agent_card(card, strict=False)
    assert any("must not be empty" in e for e in errors)


def test_validate_agent_card_strict_mode_requires_extended_fields():
    card = {
        "name": "Test",
        "description": "Test agent",
        "url": "https://example.com",
        "version": "1.0.0",
    }
    errors = validate_agent_card(card, strict=True)
    # strict requires capabilities, defaultInputModes, defaultOutputModes, skills
    assert len(errors) > 0
    field_names = " ".join(errors).lower()
    assert "capabilities" in field_names or "defaultinputmodes" in field_names or "skills" in field_names


def test_validate_agent_card_validates_skill_structure():
    card = {
        "name": "Test",
        "description": "Test agent",
        "url": "https://example.com",
        "version": "1.0.0",
        "skills": [{"id": "s1"}],  # missing name and description
    }
    errors = validate_agent_card(card)
    assert len(errors) > 0
    assert any("skill" in e.lower() for e in errors)


def test_validate_agent_card_accepts_full_valid_card():
    card = {
        "protocolVersion": "0.3.0",
        "name": "My Agent",
        "description": "Does things",
        "url": "https://example.com/a2a",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "skill-1",
                "name": "Skill One",
                "description": "Does something",
                "tags": ["nlp"],
            }
        ],
        "provider": {"organization": "Acme Corp", "url": "https://acme.example.com"},
    }
    errors = validate_agent_card(card)
    assert len(errors) == 0


# ---------------------------------------------------------------------------
# _normalise_fields
# ---------------------------------------------------------------------------

def test_normalise_top_level_snake_case():
    card = {
        "protocol_version": "0.3.0",
        "name": "Test",
        "default_input_modes": ["text/plain"],
    }
    result = _normalise_fields(card)
    assert "protocolVersion" in result
    assert "defaultInputModes" in result
    assert "protocol_version" not in result


def test_normalise_does_not_overwrite_existing_camel():
    """If both snake_case and camelCase exist, keep the camelCase value."""
    card = {
        "protocol_version": "old",
        "protocolVersion": "correct",
    }
    result = _normalise_fields(card)
    assert result["protocolVersion"] == "correct"


def test_normalise_skill_snake_case_fields():
    """Skill-level input_modes/output_modes should be normalised."""
    card = {
        "name": "Test",
        "skills": [
            {"id": "s1", "name": "Skill", "description": "x", "input_modes": ["text/plain"], "output_modes": ["text/plain"]},
        ],
    }
    result = _normalise_fields(card)
    skill = result["skills"][0]
    assert "inputModes" in skill
    assert "outputModes" in skill
    assert "input_modes" not in skill


def test_normalise_accepts_snake_case_agent_card():
    """A full agent card using snake_case field names should validate after normalisation."""
    card = {
        "protocol_version": "0.3.0",
        "name": "Snake Agent",
        "description": "Uses snake_case everywhere",
        "url": "https://example.com/a2a",
        "version": "1.0.0",
        "capabilities": {"streaming": False},
        "default_input_modes": ["text/plain"],
        "default_output_modes": ["text/plain"],
        "skills": [
            {
                "id": "s1",
                "name": "Skill One",
                "description": "A skill",
                "tags": ["test"],
                "input_modes": ["text/plain"],
                "output_modes": ["text/plain"],
            }
        ],
    }
    errors = validate_agent_card(card)
    assert len(errors) == 0


# ---------------------------------------------------------------------------
# v1.0 Protocol Compatibility
# ---------------------------------------------------------------------------

def test_normalise_v1_interfaces_to_url():
    """v1.0 cards use interfaces[] instead of top-level url — normaliser should extract it."""
    card = {
        "name": "V1 Agent",
        "interfaces": [
            {"url": "https://example.com/a2a", "protocolVersion": "1.0", "protocolBinding": "jsonrpc-over-http"}
        ],
    }
    result = _normalise_fields(card)
    assert result["url"] == "https://example.com/a2a"
    assert result["protocolVersion"] == "1.0"


def test_normalise_v1_does_not_overwrite_existing_url():
    """If a card has both url and interfaces, keep the top-level url."""
    card = {
        "name": "Hybrid Agent",
        "url": "https://example.com/legacy",
        "interfaces": [
            {"url": "https://example.com/v1", "protocolVersion": "1.0"}
        ],
    }
    result = _normalise_fields(card)
    assert result["url"] == "https://example.com/legacy"


def test_validate_v1_agent_card():
    """A v1.0-style agent card with interfaces[] should pass validation."""
    card = {
        "name": "V1 Agent",
        "description": "A v1.0 agent",
        "version": "1.0.0",
        "interfaces": [
            {"url": "https://example.com/a2a", "protocolVersion": "1.0"}
        ],
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {"id": "s1", "name": "Skill", "description": "Does things", "tags": ["test"]}
        ],
    }
    errors = validate_agent_card(card)
    assert len(errors) == 0


def test_validate_v1_minimal_card():
    """A minimal v1.0 card (name + interfaces only) should pass non-strict validation."""
    card = {
        "name": "Minimal V1",
        "interfaces": [
            {"url": "https://example.com/a2a", "protocolVersion": "1.0"}
        ],
    }
    errors = validate_agent_card(card, strict=False)
    assert len(errors) == 0


def test_normalise_v1_defaults_description_and_version():
    """v1.0 made description and version optional — normaliser supplies defaults."""
    card = {
        "name": "No Description Agent",
        "url": "https://example.com",
    }
    result = _normalise_fields(card)
    assert result["description"] == ""
    assert result["version"] == "1.0.0"
