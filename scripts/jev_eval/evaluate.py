"""Evaluate the Jev Agent Card classifier against owner-labelled and synthetic cards.

Run from backend/ (it imports the production classifier):

    cd backend && uv run python ../scripts/jev_eval/evaluate.py [--config CFG.json] [--refetch]

Without --config it scores the production PREAMBLE/QUESTIONS. A candidate config is
{"preamble": str, "questions": {name: {"q": str, "true": str, "false": str}}}.

Cards are fetched live through the audit script's SSRF-guarded fetcher and cached; Jev
answers are cached per config, so re-evaluating costs nothing. Labels come from
labels.json (owner decisions and adjudicated reviews); unlabelled cards count as accept.
Cards are split into dev/hold by a stable hash: tune on dev, judge on hold.
"""

import argparse
import asyncio
import hashlib
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.card_classifier import PREAMBLE, QUESTIONS, CardClassifierError, card_windows
from app.config import settings
from typesafe_sdk import AsyncTypeSafeClient, Noul

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import audit_agent_cards  # noqa: E402
from synthetic import SYNTHETIC  # noqa: E402

CACHE = Path("/tmp/a2a-jev-eval")
API = "https://a2aregistry.org/api"


def production_config() -> dict:
    return {
        "preamble": PREAMBLE,
        "questions": {k: {"q": q, "true": t, "false": f} for k, (q, t, f) in QUESTIONS.items()},
    }


def live_cards(refetch: bool) -> dict[str, dict]:
    path = CACHE / "cards.json"
    if path.exists() and not refetch:
        return json.loads(path.read_text())
    agents = audit_agent_cards.fetch_agents(API, 20)

    def get(agent):
        try:
            card, _ = audit_agent_cards.fetch_json(agent["wellKnownURI"], 15)
            return agent["id"], card if isinstance(card, dict) else None
        except Exception:
            return agent["id"], None

    with ThreadPoolExecutor(16) as pool:
        cards = {i: c for i, c in pool.map(get, agents) if c is not None}
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cards))
    return cards


def dataset(refetch: bool) -> dict[str, dict]:
    labels = json.loads((HERE / "labels.json").read_text())
    data = {}
    for i, card in live_cards(refetch).items():
        split = "dev" if int(hashlib.sha256(i.encode()).hexdigest(), 16) % 2 == 0 else "hold"
        label = int(labels.get(i, {}).get("label") == "reject")
        data[i] = {"card": card, "label": label, "split": split}
    for i, (card, label) in SYNTHETIC.items():
        data[i] = {"card": card, "label": int(label == "reject"), "split": "syn"}
    return data


async def score_all(data: dict, cfg: dict) -> dict[str, dict | None]:
    cfg_hash = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    cache = CACHE / cfg_hash
    cache.mkdir(parents=True, exist_ok=True)
    questions = {
        name: Noul(
            instructions=f"{cfg['preamble']}\n\n{q['q']}",
            criteria={"true": q["true"], "false": q["false"]},
        )
        for name, q in cfg["questions"].items()
    }
    client = AsyncTypeSafeClient(api_key=settings.jev_api_key)
    sem = asyncio.Semaphore(12)

    async def one(cid: str):
        path = cache / f"{hashlib.sha256(cid.encode()).hexdigest()[:16]}.json"
        if path.exists():
            return cid, json.loads(path.read_text())
        try:
            windows = card_windows(data[cid]["card"])
        except CardClassifierError:
            result = None  # held in production: too large or overlong keys
        else:
            signals: dict[str, float] = {}
            for window in windows:
                async with sem:
                    reply = await client.system_one(window, questions, model=settings.jev_model)
                for name, answer in reply.answers.items():
                    signals[name] = max(signals.get(name, 0.0), float(answer.noul))
            result = signals
        path.write_text(json.dumps(result))
        return cid, result

    return dict(await asyncio.gather(*(one(i) for i in data)))


def average_precision(scores: dict, ids: list, data: dict) -> float:
    hits = total = 0
    for rank, i in enumerate(sorted(ids, key=lambda i: -scores[i]), 1):
        if data[i]["label"]:
            hits += 1
            total += hits / rank
    return round(total / max(hits, 1), 3)


def at(scores: dict, ids: list, data: dict, t: float) -> str:
    held = [i for i in ids if scores[i] >= t]
    caught = sum(data[i]["label"] for i in held)
    rejects = sum(data[i]["label"] for i in ids)
    false_holds = 100 * (len(held) - caught) / max(len(ids), 1)
    return f"{caught}/{rejects} caught, {false_holds:.1f} false holds/100"


def report(signals: dict, data: dict) -> None:
    aggregations = {
        "max (production)": lambda s: max(s.values()),
        "noisy-or": lambda s: 1 - math.prod(1 - p for p in s.values()),
    }
    by_split = {s: [i for i in data if data[i]["split"] == s] for s in ("dev", "hold", "syn")}
    for name, aggregate in aggregations.items():
        scores = {i: 1.0 if s is None else aggregate(s) for i, s in signals.items()}
        best = max(
            (x / 100 for x in range(5, 100)),
            key=lambda t: 2
            * sum(data[i]["label"] for i in by_split["dev"] if scores[i] >= t)
            / max(
                sum(scores[i] >= t for i in by_split["dev"])
                + sum(data[i]["label"] for i in by_split["dev"]),
                1,
            ),
        )
        print(f"\n{name}")
        print(
            f"  AP dev {average_precision(scores, by_split['dev'], data)}"
            f" | AP hold {average_precision(scores, by_split['hold'], data)}"
        )
        for label, t in (
            ("production threshold", settings.jev_threshold),
            ("best dev threshold", best),
        ):
            print(
                f"  {label} {t:.2f}: hold {at(scores, by_split['hold'], data, t)}"
                f" | synthetic {at(scores, by_split['syn'], data, t)}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--config", type=Path, help="candidate prompt config JSON (default: production)"
    )
    parser.add_argument(
        "--refetch", action="store_true", help="re-fetch live cards instead of the cache"
    )
    args = parser.parse_args()
    if not settings.jev_api_key:
        raise SystemExit("Set JEV_API_KEY")
    cfg = json.loads(args.config.read_text()) if args.config else production_config()
    data = dataset(args.refetch)
    live = [d for d in data.values() if d["split"] != "syn"]
    rejects = sum(d["label"] for d in live)
    print(f"{len(live)} live cards ({rejects} labelled reject) + {len(SYNTHETIC)} synthetic")
    report(asyncio.run(score_all(data, cfg)), data)


if __name__ == "__main__":
    main()
