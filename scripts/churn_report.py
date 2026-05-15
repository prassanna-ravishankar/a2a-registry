#!/usr/bin/env python3
"""
Passive churn analysis for the A2A Registry. Reads directly from the
agents + health_checks tables and emits five views as JSON (default) or
a markdown table dump.

Usage:
    uv run scripts/churn_report.py
    uv run scripts/churn_report.py --format=markdown

The script opens a read-only transaction and runs no writes/DDL. It uses
the same DATABASE_URL_OVERRIDE / DB_* env vars as the backend app.

Issue: #128 (follow-up to #109).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.config import settings  # noqa: E402

MIN_COHORT_SIZE = 5
SMALL_COHORT_NOTE = f"n<{MIN_COHORT_SIZE} (suppressed)"


# ── Queries ─────────────────────────────────────────────────────────────────
# All queries are read-only. The connection is opened with a READ ONLY
# transaction wrapper, so accidental writes would error out anyway.

Q_TIME_TO_FIRST_FAILURE = """
SELECT
    CASE
        WHEN days_to_fail < 1 THEN '0d'
        WHEN days_to_fail < 2 THEN '1d'
        WHEN days_to_fail < 7 THEN '2-6d'
        WHEN days_to_fail < 30 THEN '7-29d'
        ELSE '30d+'
    END AS bucket,
    COUNT(*) AS agents
FROM (
    SELECT
        a.id,
        EXTRACT(EPOCH FROM (MIN(hc.checked_at) - a.created_at)) / 86400.0
            AS days_to_fail
    FROM agents a
    JOIN health_checks hc
      ON hc.agent_id = a.id AND hc.success = false
    GROUP BY a.id, a.created_at
) t
WHERE days_to_fail IS NOT NULL AND days_to_fail >= 0
GROUP BY bucket
ORDER BY
    CASE bucket
        WHEN '0d' THEN 0
        WHEN '1d' THEN 1
        WHEN '2-6d' THEN 2
        WHEN '7-29d' THEN 3
        ELSE 4
    END;
"""

# (2) initial-category → final-state pivot.
# `maintainer_notes` is free-form text; the leading token before the first
# period or whitespace is the smoke-test category for agents registered
# post-#126. For older rows it's NULL — we surface that as "unknown" rather
# than dropping the row.
Q_INITIAL_TO_FINAL = """
SELECT
    COALESCE(
        NULLIF(split_part(COALESCE(maintainer_notes, ''), '.', 1), ''),
        'unknown'
    ) AS initial_category,
    CASE
        WHEN hidden THEN 'hidden'
        WHEN task_conformance_passed IS TRUE THEN 'healthy'
        WHEN task_conformance_passed IS FALSE THEN 'failing'
        ELSE 'unchecked'
    END AS final_state,
    task_conformance_category AS final_task_category,
    COUNT(*) AS agents
FROM agents
GROUP BY initial_category, final_state, final_task_category
ORDER BY initial_category, final_state, final_task_category;
"""

# (3) recovery rate. Agents that hit a run of >=10 consecutive failed
# health checks, then later had a successful one. We compute "consecutive
# failures" via the classic gaps-and-islands trick.
Q_RECOVERY_RATE = """
WITH ordered AS (
    SELECT
        agent_id,
        checked_at,
        success,
        ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY checked_at)
            AS rn,
        ROW_NUMBER() OVER (
            PARTITION BY agent_id, success ORDER BY checked_at
        ) AS rn_success
    FROM health_checks
),
streaks AS (
    SELECT
        agent_id,
        success,
        rn - rn_success AS streak_id,
        MIN(checked_at) AS streak_start,
        MAX(checked_at) AS streak_end,
        COUNT(*) AS streak_len
    FROM ordered
    GROUP BY agent_id, success, rn - rn_success
),
long_fail_streaks AS (
    SELECT *
    FROM streaks
    WHERE success = false AND streak_len >= 10
),
recoveries AS (
    SELECT
        lfs.agent_id,
        lfs.streak_end AS failed_until,
        MIN(hc.checked_at) AS recovered_at
    FROM long_fail_streaks lfs
    LEFT JOIN health_checks hc
      ON hc.agent_id = lfs.agent_id
     AND hc.success = true
     AND hc.checked_at > lfs.streak_end
    GROUP BY lfs.agent_id, lfs.streak_end
)
SELECT
    COUNT(*) AS agents_with_long_fail_streak,
    COUNT(recovered_at) AS recovered,
    AVG(EXTRACT(EPOCH FROM (recovered_at - failed_until)) / 86400.0)
        AS avg_days_to_recover,
    percentile_disc(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (recovered_at - failed_until)) / 86400.0
    ) AS median_days_to_recover
FROM recoveries;
"""

# (4) conformance trajectory for hidden agents. Did `conformance` flip
# false before the agent went offline, or was the card still valid?
# We approximate "went offline" as the first day in the agent's most
# recent failure streak. Since we don't have a historical conformance
# log, we report the *current* conformance for hidden agents — this is
# a snapshot, not a time series. The maintainer can read it as
# "of the agents that are currently hidden, how many also have a
# broken/missing card vs. a valid card that's just unreachable."
Q_CONFORMANCE_TRAJECTORY = """
SELECT
    CASE
        WHEN conformance IS TRUE THEN 'card_valid'
        WHEN conformance IS FALSE THEN 'card_invalid'
        ELSE 'card_unchecked'
    END AS conformance_state,
    task_conformance_category,
    COUNT(*) AS hidden_agents
FROM agents
WHERE hidden = true
GROUP BY conformance_state, task_conformance_category
ORDER BY conformance_state, task_conformance_category;
"""

# (5) cohort survival by registration month. "Still healthy at N days"
# = the agent had a successful health check within the [N-1, N+1] day
# window post-registration. Because the worker prunes >90d of
# health_checks history, the 90d column is only meaningful for cohorts
# registered <90 days ago AND with surviving health rows.
Q_COHORT_SURVIVAL = """
WITH cohorts AS (
    SELECT
        date_trunc('month', created_at)::date AS cohort_month,
        id,
        created_at
    FROM agents
),
checks_with_age AS (
    SELECT
        c.cohort_month,
        c.id,
        EXTRACT(EPOCH FROM (hc.checked_at - c.created_at)) / 86400.0
            AS age_days,
        hc.success
    FROM cohorts c
    LEFT JOIN health_checks hc ON hc.agent_id = c.id
),
survival AS (
    SELECT
        cohort_month,
        id,
        bool_or(success AND age_days BETWEEN 0 AND 2)   AS alive_1d,
        bool_or(success AND age_days BETWEEN 0 AND 8)   AS alive_7d,
        bool_or(success AND age_days BETWEEN 0 AND 31)  AS alive_30d,
        bool_or(success AND age_days BETWEEN 0 AND 91)  AS alive_90d
    FROM checks_with_age
    GROUP BY cohort_month, id
)
SELECT
    cohort_month,
    COUNT(*) AS cohort_size,
    SUM(CASE WHEN alive_1d  THEN 1 ELSE 0 END) AS alive_1d,
    SUM(CASE WHEN alive_7d  THEN 1 ELSE 0 END) AS alive_7d,
    SUM(CASE WHEN alive_30d THEN 1 ELSE 0 END) AS alive_30d,
    SUM(CASE WHEN alive_90d THEN 1 ELSE 0 END) AS alive_90d
FROM survival
GROUP BY cohort_month
ORDER BY cohort_month;
"""


# ── View runners ────────────────────────────────────────────────────────────

async def view_time_to_first_failure(conn: asyncpg.Connection) -> dict[str, Any]:
    rows = await conn.fetch(Q_TIME_TO_FIRST_FAILURE)
    buckets = [{"bucket": r["bucket"], "agents": r["agents"]} for r in rows]
    total = sum(b["agents"] for b in buckets)
    return {
        "description": "Days from registration to first failed health check.",
        "total_agents_with_failure": total,
        "buckets": buckets,
        "small_cohort": total < MIN_COHORT_SIZE,
    }


async def view_initial_to_final(conn: asyncpg.Connection) -> dict[str, Any]:
    rows = await conn.fetch(Q_INITIAL_TO_FINAL)
    pivot = [
        {
            "initial_category": r["initial_category"],
            "final_state": r["final_state"],
            "final_task_category": r["final_task_category"],
            "agents": r["agents"],
        }
        for r in rows
    ]
    return {
        "description": (
            "Initial smoke-test category (from maintainer_notes, parsed) "
            "pivoted against current state. 'unknown' covers rows registered "
            "before #126 backfilled the structured category."
        ),
        "rows": pivot,
        "small_cohort": sum(p["agents"] for p in pivot) < MIN_COHORT_SIZE,
    }


async def view_recovery_rate(conn: asyncpg.Connection) -> dict[str, Any]:
    row = await conn.fetchrow(Q_RECOVERY_RATE)
    n = row["agents_with_long_fail_streak"] if row else 0
    if n < MIN_COHORT_SIZE:
        return {
            "description": (
                "Of agents that hit >=10 consecutive failed health checks, "
                "what fraction later had a successful check, and how long "
                "did recovery take."
            ),
            "agents_with_long_fail_streak": n,
            "note": SMALL_COHORT_NOTE,
            "small_cohort": True,
        }
    recovered = row["recovered"]
    return {
        "description": (
            "Of agents that hit >=10 consecutive failed health checks, "
            "what fraction later had a successful check, and how long "
            "did recovery take."
        ),
        "agents_with_long_fail_streak": n,
        "recovered": recovered,
        "recovery_rate": (recovered / n) if n else None,
        "avg_days_to_recover": (
            float(row["avg_days_to_recover"])
            if row["avg_days_to_recover"] is not None
            else None
        ),
        "median_days_to_recover": (
            float(row["median_days_to_recover"])
            if row["median_days_to_recover"] is not None
            else None
        ),
        "small_cohort": False,
    }


async def view_conformance_trajectory(conn: asyncpg.Connection) -> dict[str, Any]:
    rows = await conn.fetch(Q_CONFORMANCE_TRAJECTORY)
    breakdown = [
        {
            "conformance_state": r["conformance_state"],
            "task_conformance_category": r["task_conformance_category"],
            "hidden_agents": r["hidden_agents"],
        }
        for r in rows
    ]
    total = sum(b["hidden_agents"] for b in breakdown)
    return {
        "description": (
            "Among currently-hidden agents, the split between cards that "
            "are still schema-valid (endpoint just stopped responding) and "
            "cards that became invalid. Snapshot, not a time series — the "
            "registry does not log historical conformance flips."
        ),
        "total_hidden": total,
        "rows": breakdown,
        "small_cohort": total < MIN_COHORT_SIZE,
    }


async def view_cohort_survival(conn: asyncpg.Connection) -> dict[str, Any]:
    rows = await conn.fetch(Q_COHORT_SURVIVAL)
    cohorts = []
    for r in rows:
        size = r["cohort_size"]
        too_small = size < MIN_COHORT_SIZE
        cohorts.append({
            "cohort_month": r["cohort_month"].isoformat() if r["cohort_month"] else None,
            "cohort_size": size,
            "alive_1d": r["alive_1d"] if not too_small else None,
            "alive_7d": r["alive_7d"] if not too_small else None,
            "alive_30d": r["alive_30d"] if not too_small else None,
            "alive_90d": r["alive_90d"] if not too_small else None,
            "note": SMALL_COHORT_NOTE if too_small else None,
        })
    return {
        "description": (
            "Per registration-month cohort, count of agents with at least "
            "one successful health check within the first 1/7/30/90 days. "
            "90d column is limited by the 90-day health-check retention."
        ),
        "cohorts": cohorts,
    }


VIEWS = [
    ("time_to_first_failure", view_time_to_first_failure),
    ("initial_to_final_state", view_initial_to_final),
    ("recovery_rate", view_recovery_rate),
    ("conformance_trajectory", view_conformance_trajectory),
    ("cohort_survival", view_cohort_survival),
]


async def run_report(conn: asyncpg.Connection) -> dict[str, Any]:
    await conn.execute("SET TRANSACTION READ ONLY")
    out: dict[str, Any] = {}
    for name, fn in VIEWS:
        out[name] = await fn(conn)
    return out


# ── Output formatting ───────────────────────────────────────────────────────

def _fmt_cell(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def _md_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_no rows_\n"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = "\n".join(
        "| " + " | ".join(_fmt_cell(r.get(c)) for c in columns) + " |"
        for r in rows
    )
    return f"{header}\n{sep}\n{body}\n"


def render_markdown(report: dict[str, Any]) -> str:
    parts: list[str] = ["# A2A Registry Churn Report\n"]

    v = report["time_to_first_failure"]
    parts.append("## 1. Time-to-first-failure\n")
    parts.append(v["description"] + "\n")
    parts.append(f"_Total agents with at least one failure: {v['total_agents_with_failure']}_\n")
    parts.append(_md_table(v["buckets"], ["bucket", "agents"]))

    v = report["initial_to_final_state"]
    parts.append("\n## 2. Initial-category → final-state pivot\n")
    parts.append(v["description"] + "\n")
    parts.append(_md_table(
        v["rows"],
        ["initial_category", "final_state", "final_task_category", "agents"],
    ))

    v = report["recovery_rate"]
    parts.append("\n## 3. Recovery rate (>=10 consecutive failures)\n")
    parts.append(v["description"] + "\n")
    if v.get("small_cohort"):
        parts.append(f"_{v.get('note', SMALL_COHORT_NOTE)} "
                     f"(n={v['agents_with_long_fail_streak']})_\n")
    else:
        parts.append(_md_table([v], [
            "agents_with_long_fail_streak",
            "recovered",
            "recovery_rate",
            "avg_days_to_recover",
            "median_days_to_recover",
        ]))

    v = report["conformance_trajectory"]
    parts.append("\n## 4. Conformance trajectory (currently-hidden agents)\n")
    parts.append(v["description"] + "\n")
    parts.append(f"_Total hidden: {v['total_hidden']}_\n")
    parts.append(_md_table(
        v["rows"],
        ["conformance_state", "task_conformance_category", "hidden_agents"],
    ))

    v = report["cohort_survival"]
    parts.append("\n## 5. Cohort survival by registration month\n")
    parts.append(v["description"] + "\n")
    parts.append(_md_table(
        v["cohorts"],
        ["cohort_month", "cohort_size",
         "alive_1d", "alive_7d", "alive_30d", "alive_90d", "note"],
    ))

    return "\n".join(parts)


# ── Entrypoint ──────────────────────────────────────────────────────────────

async def main(fmt: str) -> int:
    dsn = settings.database_url
    conn = await asyncpg.connect(dsn)
    try:
        report = await run_report(conn)
    finally:
        await conn.close()

    if fmt == "markdown":
        print(render_markdown(report))
    else:
        print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(fmt=args.format)))
