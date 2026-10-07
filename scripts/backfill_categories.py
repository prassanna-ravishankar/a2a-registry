"""One-off: assign Jev categories to agents classified before categories existed.

Run from backend/ with DB settings pointing at the target database (e.g. via a
kubectl port-forward to the Cloud SQL proxy) and JEV_API_KEY set:

    cd backend && uv run python ../scripts/backfill_categories.py          # dry run
    cd backend && uv run python ../scripts/backfill_categories.py --apply

Each agent is classified on exactly what the worker would classify (its stored
record, refreshed from the live card, plus that card), and only the category
fields are written, guarded by the review revision. Review status, score and
fingerprint are never touched, so no agent's visibility can change.
"""

import asyncio
import sys
from collections import Counter

import aiohttp
import worker
from app import card_classifier
from app.card_classifier import CardClassifierError, classify_card, review_document
from app.database import db
from app.repositories import AgentRepository
from app.validators import _normalise_fields, validate_agent_card

APPLY = "--apply" in sys.argv
card_classifier._inflight = asyncio.Semaphore(48)  # Jev throughput peaks around 48 in flight


def worker_document(stored, card: dict) -> dict:
    """The review document the worker builds for this record and live card."""
    changed = {}
    if not validate_agent_card(card, strict=True):
        present = worker._present_card_fields(card, _normalise_fields(card))
        changed = {
            f: v
            for f, v in present.items()
            if worker._comparable(getattr(stored, f, None)) != worker._comparable(v)
        }
    _, candidate = worker._material_changes(stored, changed)
    return review_document(candidate, card)


async def one(
    repo: AgentRepository, session: aiohttp.ClientSession, sem: asyncio.Semaphore, agent_id
) -> tuple:
    async with sem:
        snapshot = await repo.get_review_snapshot(agent_id)
        if snapshot is None:
            return ("gone", None)
        stored, state = snapshot
        try:
            async with session.get(
                str(stored.wellKnownURI),
                timeout=aiohttp.ClientTimeout(total=10),
                headers={
                    "User-Agent": "A2A-Registry-HealthCheck/1.0",
                    "Accept": "application/json",
                },
            ) as response:
                card = (
                    await response.json(content_type=None) if 200 <= response.status < 300 else None
                )
        except Exception:
            card = None
        if not isinstance(card, dict):
            return ("unreachable", None)
        try:
            verdict = await classify_card(worker_document(stored, card))
        except CardClassifierError:
            return ("jev_error", None)
        if not APPLY:
            return ("would set", verdict.category)
        written = await repo.set_category(agent_id, verdict, state["review_revision"])
        return ("set" if written else "raced", verdict.category)


async def main() -> None:
    await db.connect()
    rows = await db.fetch("SELECT id FROM agents WHERE hidden = false AND category IS NULL")
    repo = AgentRepository(db)
    sem = asyncio.Semaphore(32)
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(one(repo, session, sem, r["id"]) for r in rows))
    print("mode:", "APPLY" if APPLY else "DRY RUN", "| agents without a category:", len(rows))
    print("outcomes:", dict(Counter(outcome for outcome, _ in results)))
    print("categories:", dict(Counter(c for _, c in results if c).most_common()))


if __name__ == "__main__":
    asyncio.run(main())
