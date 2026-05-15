"""Tests for scripts/churn_report.py.

We mock the asyncpg connection and feed each view its expected row shape.
Per-view tests assert the output schema; an end-to-end test asserts the
top-level JSON keys and markdown rendering.
"""

import datetime as dt
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import churn_report as cr  # noqa: E402


def _make_conn(fetch_map=None, fetchrow_map=None):
    """Build a mock asyncpg connection.

    fetch_map / fetchrow_map are dicts keyed by a substring of the query
    so each view can be addressed independently.
    """
    fetch_map = fetch_map or {}
    fetchrow_map = fetchrow_map or {}

    async def fetch(query, *args):
        for needle, rows in fetch_map.items():
            if needle in query:
                return rows
        return []

    async def fetchrow(query, *args):
        for needle, row in fetchrow_map.items():
            if needle in query:
                return row
        return None

    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=fetch)
    conn.fetchrow = AsyncMock(side_effect=fetchrow)
    conn.execute = AsyncMock(return_value="OK")
    return conn


# ── Per-view tests ──────────────────────────────────────────────────────────

async def test_time_to_first_failure_shape():
    conn = _make_conn(fetch_map={"days_to_fail": [
        {"bucket": "0d", "agents": 3},
        {"bucket": "1d", "agents": 5},
        {"bucket": "7-29d", "agents": 2},
    ]})
    out = await cr.view_time_to_first_failure(conn)
    assert out["total_agents_with_failure"] == 10
    assert {b["bucket"] for b in out["buckets"]} == {"0d", "1d", "7-29d"}
    assert out["small_cohort"] is False


async def test_initial_to_final_shape():
    conn = _make_conn(fetch_map={"initial_category": [
        {"initial_category": "WORKING", "final_state": "healthy",
         "final_task_category": "WORKING", "agents": 12},
        {"initial_category": "404", "final_state": "hidden",
         "final_task_category": "404", "agents": 4},
    ]})
    out = await cr.view_initial_to_final(conn)
    assert len(out["rows"]) == 2
    assert out["rows"][0]["initial_category"] == "WORKING"
    assert out["small_cohort"] is False


async def test_recovery_rate_normal():
    conn = _make_conn(fetchrow_map={"long_fail_streaks": {
        "agents_with_long_fail_streak": 10,
        "recovered": 3,
        "avg_days_to_recover": 4.5,
        "median_days_to_recover": 3.0,
    }})
    out = await cr.view_recovery_rate(conn)
    assert out["recovery_rate"] == 0.3
    assert out["avg_days_to_recover"] == 4.5
    assert out["small_cohort"] is False


async def test_recovery_rate_small_cohort_suppressed():
    conn = _make_conn(fetchrow_map={"long_fail_streaks": {
        "agents_with_long_fail_streak": 2,
        "recovered": 1,
        "avg_days_to_recover": 1.0,
        "median_days_to_recover": 1.0,
    }})
    out = await cr.view_recovery_rate(conn)
    assert out["small_cohort"] is True
    assert "recovery_rate" not in out
    assert cr.SMALL_COHORT_NOTE in out["note"]


async def test_conformance_trajectory_shape():
    conn = _make_conn(fetch_map={"conformance_state": [
        {"conformance_state": "card_valid", "task_conformance_category": "404",
         "hidden_agents": 7},
        {"conformance_state": "card_invalid", "task_conformance_category": None,
         "hidden_agents": 2},
    ]})
    out = await cr.view_conformance_trajectory(conn)
    assert out["total_hidden"] == 9
    assert any(r["conformance_state"] == "card_valid" for r in out["rows"])


async def test_cohort_survival_suppresses_small_cohorts():
    conn = _make_conn(fetch_map={"cohort_month": [
        {"cohort_month": dt.date(2026, 1, 1), "cohort_size": 12,
         "alive_1d": 11, "alive_7d": 9, "alive_30d": 7, "alive_90d": 5},
        {"cohort_month": dt.date(2026, 2, 1), "cohort_size": 3,
         "alive_1d": 2, "alive_7d": 1, "alive_30d": 1, "alive_90d": 0},
    ]})
    out = await cr.view_cohort_survival(conn)
    big, small = out["cohorts"]
    assert big["alive_1d"] == 11
    assert small["alive_1d"] is None
    assert small["note"] == cr.SMALL_COHORT_NOTE


# ── End-to-end ──────────────────────────────────────────────────────────────

async def test_run_report_returns_all_views():
    conn = _make_conn(
        fetch_map={
            "days_to_fail": [{"bucket": "0d", "agents": 1}],
            "initial_category": [],
            "conformance_state": [],
            "cohort_month": [],
        },
        fetchrow_map={"long_fail_streaks": {
            "agents_with_long_fail_streak": 0,
            "recovered": 0,
            "avg_days_to_recover": None,
            "median_days_to_recover": None,
        }},
    )
    report = await cr.run_report(conn)
    assert set(report.keys()) == {
        "time_to_first_failure",
        "initial_to_final_state",
        "recovery_rate",
        "conformance_trajectory",
        "cohort_survival",
    }
    conn.execute.assert_awaited_with("SET TRANSACTION READ ONLY")
    # JSON-serializable.
    json.dumps(report, default=str)


async def test_markdown_renders_all_sections():
    conn = _make_conn(
        fetch_map={
            "days_to_fail": [{"bucket": "0d", "agents": 6}],
            "initial_category": [
                {"initial_category": "WORKING", "final_state": "healthy",
                 "final_task_category": "WORKING", "agents": 9},
            ],
            "conformance_state": [
                {"conformance_state": "card_valid",
                 "task_conformance_category": "404", "hidden_agents": 6},
            ],
            "cohort_month": [
                {"cohort_month": dt.date(2026, 1, 1), "cohort_size": 8,
                 "alive_1d": 7, "alive_7d": 5, "alive_30d": 3, "alive_90d": 1},
            ],
        },
        fetchrow_map={"long_fail_streaks": {
            "agents_with_long_fail_streak": 10,
            "recovered": 4,
            "avg_days_to_recover": 2.0,
            "median_days_to_recover": 2.0,
        }},
    )
    report = await cr.run_report(conn)
    md = cr.render_markdown(report)
    for section in (
        "1. Time-to-first-failure",
        "2. Initial-category",
        "3. Recovery rate",
        "4. Conformance trajectory",
        "5. Cohort survival",
    ):
        assert section in md


pytestmark = pytest.mark.asyncio


async def test_format_cell_handles_none_and_floats():
    assert cr._fmt_cell(None) == "—"
    assert cr._fmt_cell(1.2345) == "1.23"
    assert cr._fmt_cell("x") == "x"
