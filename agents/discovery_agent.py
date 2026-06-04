"""
agents/discovery_agent.py — Runs all 4 discovery sources in parallel and merges results.
LangGraph node: run_discovery(state) → state with raw_repos populated.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from core.github_client import get_trending_repos, search_github_repos
from core.hn_client import get_show_hn_repos
from core.reddit_client import get_reddit_repos

logger = logging.getLogger(__name__)


def run_discovery(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — runs all 4 discovery sources concurrently, merges results,
    deduplicates by full_name within this batch, and updates state["raw_repos"].
    """
    logger.info("[Discovery] Starting parallel source collection...")

    sources = {
        "github_trending": get_trending_repos,
        "github_search": search_github_repos,
        "hn": get_show_hn_repos,
        "reddit": get_reddit_repos,
    }

    results: list[dict] = []
    errors: list[str] = list(state.get("errors", []))

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): name for name, fn in sources.items()}

        for future in as_completed(futures):
            source_name = futures[future]
            try:
                repos = future.result()
                logger.info(f"[Discovery] {source_name}: {len(repos)} repos")
                results.extend(repos)
            except Exception as e:
                msg = f"[Discovery] Source '{source_name}' failed: {e}"
                logger.error(msg)
                errors.append(msg)

    # Deduplicate by full_name within this batch (keep first occurrence)
    seen: set[str] = set()
    deduplicated: list[dict] = []
    for repo in results:
        fn = repo.get("full_name", "").lower().strip()
        if fn and fn not in seen:
            seen.add(fn)
            deduplicated.append(repo)

    logger.info(
        f"[Discovery] Total: {len(results)} collected → {len(deduplicated)} unique after in-batch dedup"
    )

    return {
        **state,
        "raw_repos": deduplicated,
        "errors": errors,
    }
