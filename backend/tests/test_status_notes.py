"""Tests for AgentRepository.compute_status_notes — the business logic that
generates user-visible status warnings from health data."""

from app.repositories import AgentRepository


def test_no_notes_when_healthy():
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=100.0,
        last_5_worker_successes=[True, True, True, True, True],
        last_worker_error=None,
        last_10_chat_errors=[],
        conformance=True,
        conformance_errors=None,
        flag_count=0,
    )
    assert notes == []


def test_low_uptime_note():
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=30.0,
        last_5_worker_successes=[False, False, True, False, False],
        last_worker_error=None,
        last_10_chat_errors=[],
        conformance=True,
        conformance_errors=None,
        flag_count=0,
    )
    assert any("Low uptime" in n for n in notes)
    assert any("30%" in n for n in notes)


def test_degraded_uptime_note():
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=65.0,
        last_5_worker_successes=[True, True, False, True, False],
        last_worker_error=None,
        last_10_chat_errors=[],
        conformance=True,
        conformance_errors=None,
        flag_count=0,
    )
    assert any("Degraded uptime" in n for n in notes)
    assert any("65%" in n for n in notes)


def test_consistently_unreachable_note():
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=0.0,
        last_5_worker_successes=[False, False, False, False, False],
        last_worker_error=None,
        last_10_chat_errors=[],
        conformance=True,
        conformance_errors=None,
        flag_count=0,
    )
    assert any("unreachable" in n.lower() for n in notes)


def test_consistently_failing_with_error_detail():
    """When worker error is available, it should be included in the note."""
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=0.0,
        last_5_worker_successes=[False, False, False, False, False],
        last_worker_error="Agent card endpoint returned 200 but response is not valid JSON (Content-Type: text/html)",
        last_10_chat_errors=[],
        conformance=True,
        conformance_errors=None,
        flag_count=0,
    )
    assert any("not valid JSON" in n for n in notes)


def test_chat_error_note():
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=100.0,
        last_5_worker_successes=[True, True, True, True, True],
        last_worker_error=None,
        last_10_chat_errors=["Agent returned 502 Bad Gateway"],
        conformance=True,
        conformance_errors=None,
        flag_count=0,
    )
    assert any("502" in n for n in notes)


def test_non_conformant_note():
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=100.0,
        last_5_worker_successes=[True, True, True, True, True],
        last_worker_error=None,
        last_10_chat_errors=[],
        conformance=False,
        conformance_errors=["Missing field 'skills[].tags'"],
        flag_count=0,
    )
    assert any("conformance" in n.lower() for n in notes)
    assert any("skills" in n for n in notes)


def test_non_conformant_without_errors():
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=100.0,
        last_5_worker_successes=[True, True, True, True, True],
        last_worker_error=None,
        last_10_chat_errors=[],
        conformance=False,
        conformance_errors=None,
        flag_count=0,
    )
    assert any("Non-conformant" in n for n in notes)


def test_flagged_agent_note():
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=100.0,
        last_5_worker_successes=[True, True, True, True, True],
        last_worker_error=None,
        last_10_chat_errors=[],
        conformance=True,
        conformance_errors=None,
        flag_count=5,
    )
    assert any("Flagged by 5 users" in n for n in notes)


def test_flag_count_below_threshold():
    """Fewer than 3 flags should not generate a note."""
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=100.0,
        last_5_worker_successes=[True, True, True, True, True],
        last_worker_error=None,
        last_10_chat_errors=[],
        conformance=True,
        conformance_errors=None,
        flag_count=2,
    )
    assert not any("Flagged" in n for n in notes)


def test_multiple_issues_combined():
    """Multiple issues should all be reported."""
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=40.0,
        last_5_worker_successes=[False, False, False, False, False],
        last_worker_error="Timeout after 10000ms",
        last_10_chat_errors=["Timeout"],
        conformance=False,
        conformance_errors=["Missing 'url'"],
        flag_count=4,
    )
    assert len(notes) >= 4  # low uptime + unreachable + chat error + conformance + flagged


def test_none_uptime_no_crash():
    """None uptime (no data) should not crash."""
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=None,
        last_5_worker_successes=None,
        last_worker_error=None,
        last_10_chat_errors=None,
        conformance=None,
        conformance_errors=None,
        flag_count=0,
    )
    assert notes == []


def test_conformance_errors_capped_at_3():
    """Only first 3 conformance errors are shown."""
    errors = [f"Error {i}" for i in range(10)]
    notes = AgentRepository.compute_status_notes(
        uptime_percentage=100.0,
        last_5_worker_successes=[True, True, True, True, True],
        last_worker_error=None,
        last_10_chat_errors=[],
        conformance=False,
        conformance_errors=errors,
        flag_count=0,
    )
    conformance_notes = [n for n in notes if "conformance" in n.lower()]
    assert len(conformance_notes) == 3
