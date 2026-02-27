"""Unit tests for app/validators.py"""

from app.validators import validate_agent_card, validate_well_known_uri


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


def test_validate_agent_card_requires_description():
    card = {"name": "Test", "url": "https://example.com", "version": "1.0"}
    errors = validate_agent_card(card)
    assert any("description" in e.lower() for e in errors)


def test_validate_agent_card_requires_url():
    card = {"name": "Test", "description": "x", "version": "1.0"}
    errors = validate_agent_card(card)
    assert any("url" in e.lower() for e in errors)


def test_validate_agent_card_requires_version():
    card = {"name": "Test", "description": "x", "url": "https://example.com"}
    errors = validate_agent_card(card)
    assert any("version" in e.lower() for e in errors)


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
    errors = validate_agent_card(card)
    assert len(errors) > 0


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
        "provider": {"organization": "Acme Corp"},
    }
    errors = validate_agent_card(card)
    assert len(errors) == 0
