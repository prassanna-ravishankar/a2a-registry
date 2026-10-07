"""Evaluate Jev's category question against labelled cards.

Run from backend/ (it imports the production categories):

    cd backend && uv run python ../scripts/jev_eval/categories.py [CANDIDATE.json ...]

With no arguments it scores app/categories.py. A candidate is
{"instructions": str, "criteria": {slug: description}}; several run concurrently.
Cards come from evaluate.py's cache (run it with --refetch to refresh). Accuracy
is "strict" (Jev's top category is the labelled one) and "lenient" (also counts
the label's acceptable alternatives), with the dev/hold split shown so wording
is tuned on dev and judged on hold. Answers are cached per window and variant.
"""

import asyncio
import collections
import hashlib
import json
import sys
from pathlib import Path

from app.card_classifier import CardClassifierError, card_windows
from app.categories import CATEGORIES, CATEGORY_INSTRUCTIONS
from app.config import settings
from typesafe_sdk import AsyncTypeSafeClient, Choice

HERE = Path(__file__).resolve().parent
CACHE = Path("/tmp/a2a-jev-eval/categories")
CONCURRENCY = 48  # Jev throughput peaks here (~120 calls/s); higher is throttled.


def production_variant() -> dict:
    return {
        "instructions": CATEGORY_INSTRUCTIONS,
        "criteria": {c.slug: c.description for c in CATEGORIES},
    }


async def score(client, sem, cards: dict, variant: dict) -> dict:
    vhash = hashlib.sha256(json.dumps(variant, sort_keys=True).encode()).hexdigest()[:12]
    question = {
        "category": Choice(instructions=variant["instructions"], criteria=variant["criteria"])
    }

    async def window(text: str) -> dict:
        path = CACHE / f"{vhash}_{hashlib.sha256(text.encode()).hexdigest()[:20]}.json"
        if path.exists():
            return json.loads(path.read_text())
        async with sem:
            reply = await client.system_one(text, question, model=settings.jev_model)
        probs = dict(reply.answers["category"].probabilities)
        path.write_text(json.dumps(probs))
        return probs

    async def card(cid: str, c: dict):
        try:
            windows = card_windows(c)
        except CardClassifierError:
            return cid, None
        total = collections.Counter()
        for probs in await asyncio.gather(*(window(w) for w in windows)):
            for slug, p in probs.items():
                total[slug] += p / len(windows)
        return cid, total

    return dict(await asyncio.gather(*(card(i, c) for i, c in cards.items())))


def report(name: str, dists: dict, labels: dict) -> None:
    counts = collections.Counter()
    hits = collections.Counter()
    seen = collections.Counter()
    lenient = 0
    for cid, dist in dists.items():
        if not dist:
            continue
        top = dist.most_common(1)[0][0]
        counts[top] += 1
        if cid in labels:
            half = "dev" if int(hashlib.sha256(cid.encode()).hexdigest(), 16) % 2 == 0 else "hold"
            seen[half] += 1
            hits[half] += top == labels[cid]["primary"]
            lenient += top in {labels[cid]["primary"], *labels[cid]["acceptable"]}
    n = seen["dev"] + seen["hold"]
    print(
        f"\n{name}: strict {hits['dev'] + hits['hold']}/{n} (dev {hits['dev']}/{seen['dev']},"
        f" hold {hits['hold']}/{seen['hold']}), lenient {lenient}/{n}"
    )
    print("  " + ", ".join(f"{slug} {k}" for slug, k in counts.most_common()))


async def main() -> None:
    if not settings.jev_api_key:
        raise SystemExit("Set JEV_API_KEY")
    CACHE.mkdir(parents=True, exist_ok=True)
    cards = json.loads(Path("/tmp/a2a-jev-eval/cards.json").read_text())
    labels = json.loads((HERE / "category_labels.json").read_text())
    variants = {"production": production_variant()}
    variants.update({Path(p).stem: json.loads(Path(p).read_text()) for p in sys.argv[1:]})
    client = AsyncTypeSafeClient(api_key=settings.jev_api_key)
    sem = asyncio.Semaphore(CONCURRENCY)
    results = await asyncio.gather(*(score(client, sem, cards, v) for v in variants.values()))
    for name, dists in zip(variants, results):
        report(name, dists, labels)


if __name__ == "__main__":
    asyncio.run(main())
