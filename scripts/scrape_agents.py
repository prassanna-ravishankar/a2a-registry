#!/usr/bin/env python3
"""
Scrape agents from various sources and add them to the registry.

Usage:
    python scripts/scrape_agents.py --source lifie --limit 100
    python scripts/scrape_agents.py --source lifie --query "business" --limit 50
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
import requests


class AgentScraper:
    """Base class for agent scrapers"""

    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir
        self.agents_dir.mkdir(exist_ok=True)

    def scrape(self, **kwargs) -> List[Dict]:
        """Scrape agents from source. To be implemented by subclasses."""
        raise NotImplementedError

    def normalize_name(self, name: str) -> str:
        """Convert agent name to filename-safe slug"""
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        return slug

    def agent_exists(self, name: str) -> bool:
        """Check if agent already exists in registry"""
        filename = f"{self.normalize_name(name)}.json"
        return (self.agents_dir / filename).exists()

    def save_agent(self, agent: Dict) -> bool:
        """Save agent to file. Returns True if saved, False if skipped."""
        if self.agent_exists(agent['name']):
            print(f"⏭️  Skipping {agent['name']} (already exists)")
            return False

        filename = f"{self.normalize_name(agent['name'])}.json"
        filepath = self.agents_dir / filename

        with open(filepath, 'w') as f:
            json.dump(agent, f, indent=2)

        print(f"✅ Saved {agent['name']} -> {filename}")
        return True


class LifieHubScraper(AgentScraper):
    """Scraper for lifie.ai hub"""

    API_BASE = "https://hub.lifie.ai/api"
    HUB_BASE = "https://hub.lifie.ai"
    AGENT_CARD_BASE = "https://api.lifie.ai/a2a"

    def scrape(self, query: str = "business", limit: int = 100, min_similarity: float = 0.3) -> List[Dict]:
        """
        Scrape agents from lifie.ai hub

        Args:
            query: Search query (default: "business")
            limit: Max number of results (default: 100)
            min_similarity: Minimum similarity score (default: 0.3)
        """
        print(f"🔍 Searching lifie.ai hub for '{query}' (limit: {limit})...")

        url = f"{self.API_BASE}/registry/search"
        params = {
            "query": query,
            "limit": limit,
            "minsim": min_similarity
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        results = data.get('results', [])
        print(f"📦 Found {len(results)} agents")

        agents = []
        for result in results:
            agent = self._enhance_agent(result)
            agents.append(agent)

        return agents

    def _enhance_agent(self, raw_agent: Dict) -> Dict:
        """
        Enhance lifie.ai agent data to be A2A compliant

        Adds missing fields:
        - protocolVersion
        - defaultInputModes
        - skills (generic "interact" skill)
        - provider
        - conformance flag
        """
        agent_id = raw_agent.get('id', '')
        name = raw_agent.get('name', 'Unknown')
        description = raw_agent.get('description', '')

        # Generate slug for landing page URL
        slug = self.normalize_name(name)

        enhanced = {
            "protocolVersion": "0.3.0",
            "author": "Lifie.ai Hub",
            "wellKnownURI": f"{self.AGENT_CARD_BASE}/{agent_id}/agent-card.json",
            "conformance": False,  # Manually enhanced
            "name": name,
            "description": description,
            "url": f"{self.HUB_BASE}/agent/{agent_id}/{slug}",
            "version": "1.0.0",
            "capabilities": {
                "streaming": raw_agent.get('capabilities', {}).get('streaming', True),
                "pushNotifications": raw_agent.get('capabilities', {}).get('pushNotifications', False),
                "stateTransitionHistory": raw_agent.get('capabilities', {}).get('stateTransitionHistory', True)
            },
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": raw_agent.get('outputModes', ["text/plain"]),
            "skills": [
                {
                    "id": "interact",
                    "name": f"Interact with {name}",
                    "description": description,
                    "tags": self._extract_tags(description),
                    "inputModes": ["text/plain"],
                    "outputModes": raw_agent.get('outputModes', ["text/plain"])
                }
            ],
            "provider": {
                "organization": "Lifie.ai Hub",
                "url": self.HUB_BASE
            }
        }

        return enhanced

    def _extract_tags(self, description: str) -> List[str]:
        """Extract generic tags from description"""
        # Simple heuristic: add "business" tag for most lifie.ai agents
        # Could be enhanced with NLP or keyword extraction
        tags = ["business"]

        # Add category-specific tags based on keywords
        keywords = {
            "manufacturing": ["manufacturing", "machinery"],
            "consulting": ["consulting", "advisory"],
            "technology": ["technology", "software", "IT"],
            "retail": ["retail", "store", "shop"],
            "service": ["service", "services"]
        }

        desc_lower = description.lower()
        for tag, search_terms in keywords.items():
            if any(term in desc_lower for term in search_terms):
                tags.append(tag)

        return tags


def main():
    parser = argparse.ArgumentParser(description="Scrape agents from various sources")
    parser.add_argument(
        "--source",
        choices=["lifie"],
        default="lifie",
        help="Source to scrape from (default: lifie)"
    )
    parser.add_argument(
        "--query",
        default="business",
        help="Search query (default: business)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of results (default: 100)"
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.3,
        help="Minimum similarity score for lifie.ai (default: 0.3)"
    )
    parser.add_argument(
        "--agents-dir",
        type=Path,
        default=Path(__file__).parent.parent / "agents",
        help="Directory to save agents (default: ../agents)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't save agents, just show what would be scraped"
    )

    args = parser.parse_args()

    # Initialize scraper based on source
    if args.source == "lifie":
        scraper = LifieHubScraper(args.agents_dir)
    else:
        print(f"❌ Unknown source: {args.source}")
        sys.exit(1)

    # Scrape agents
    try:
        agents = scraper.scrape(
            query=args.query,
            limit=args.limit,
            min_similarity=args.min_similarity
        )
    except Exception as e:
        print(f"❌ Error scraping agents: {e}")
        sys.exit(1)

    if not agents:
        print("⚠️  No agents found")
        sys.exit(0)

    # Save agents
    if args.dry_run:
        print(f"\n🔍 DRY RUN - Would save {len(agents)} agents:")
        for agent in agents:
            filename = f"{scraper.normalize_name(agent['name'])}.json"
            exists = scraper.agent_exists(agent['name'])
            status = "exists" if exists else "new"
            print(f"  - {agent['name']} -> {filename} ({status})")
    else:
        print(f"\n💾 Saving {len(agents)} agents...")
        saved_count = 0
        skipped_count = 0

        for agent in agents:
            if scraper.save_agent(agent):
                saved_count += 1
            else:
                skipped_count += 1

        print(f"\n✨ Done! Saved {saved_count} new agents, skipped {skipped_count} existing")


if __name__ == "__main__":
    main()
