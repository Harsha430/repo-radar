"""
core/hn_client.py — Hacker News Algolia API client for Show HN posts.
Extracts GitHub repository links from posts in the last N hours.
"""

import logging
import re
import time
from datetime import datetime, timedelta, timezone

import requests

from config.settings import HN_LOOKBACK_HOURS

logger = logging.getLogger(__name__)

HN_ALGOLIA_API = "https://hn.algolia.com/api/v1/search"
GITHUB_URL_PATTERN = re.compile(
    r"github\.com/([a-zA-Z0-9_.\-]+/[a-zA-Z0-9_.\-]+?)(?:[/?#\s]|$)"
)


def get_show_hn_repos(hours: int = HN_LOOKBACK_HOURS) -> list[dict]:
    """
    Fetch Show HN posts from the last `hours` hours and extract GitHub repo links.
    Returns a list of raw repo dicts: [{"full_name": "...", "source": "hn", "source_metadata": {...}}]
    """
    logger.info(f"[HN] Fetching Show HN posts from the last {hours} hours...")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_ts = int(cutoff.timestamp())

    seen: set[str] = set()
    repos: list[dict] = []
    page = 0

    while True:
        try:
            resp = requests.get(
                HN_ALGOLIA_API,
                params={
                    "query": "Show HN",
                    "tags": "story",
                    "numericFilters": f"created_at_i>{cutoff_ts}",
                    "hitsPerPage": 50,
                    "page": page,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[HN] API request failed (page {page}): {e}")
            break

        hits = data.get("hits", [])
        if not hits:
            break

        for hit in hits:
            title: str = hit.get("title", "")
            url: str = hit.get("url", "") or ""
            story_text: str = hit.get("story_text", "") or ""

            # Search in URL first, then title + text
            candidates = [url, title, story_text]
            for text in candidates:
                matches = GITHUB_URL_PATTERN.findall(text)
                for match in matches:
                    fn = _clean_full_name(match)
                    if fn and fn not in seen:
                        seen.add(fn)
                        repos.append({
                            "full_name": fn,
                            "source": "hn",
                            "source_metadata": {
                                "hn_id": hit.get("objectID"),
                                "hn_title": title,
                                "hn_points": hit.get("points", 0),
                                "hn_comments": hit.get("num_comments", 0),
                                "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                            },
                        })

        # Check if more pages
        total_pages = data.get("nbPages", 1)
        page += 1
        if page >= total_pages:
            break

        time.sleep(0.2)  # Be polite to Algolia

    logger.info(f"[HN] Found {len(repos)} unique GitHub repos from Show HN")
    return repos


def _clean_full_name(raw: str) -> str | None:
    """Strip trailing .git, extra path components, and validate owner/repo format."""
    # Remove .git suffix
    raw = raw.rstrip("/").removesuffix(".git")
    # Only accept owner/repo — no deeper paths
    parts = raw.split("/")
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    # Basic sanity: non-empty, no spaces
    if not owner or not repo or " " in owner or " " in repo:
        return None
    return f"{owner}/{repo}"
