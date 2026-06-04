"""
core/reddit_client.py — Reddit PRAW client for extracting GitHub repos from multiple subreddits.
Uses read-only (script app) authentication — no user account needed.
"""

import logging
import re

import praw

from config.settings import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_SUBREDDITS,
    REDDIT_POST_LIMIT,
    REDDIT_USER_AGENT,
)

logger = logging.getLogger(__name__)

GITHUB_URL_PATTERN = re.compile(
    r"github\.com/([a-zA-Z0-9_.\-]+/[a-zA-Z0-9_.\-]+?)(?:[/?#\s\)]|$)"
)


def _get_reddit_client() -> praw.Reddit:
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )


def get_reddit_repos(
    subreddits: list[str] | None = None,
    limit: int = REDDIT_POST_LIMIT,
) -> list[dict]:
    """
    Scan hot + new posts across the given subreddits and extract GitHub repo links.
    Also scans the URL field of link posts.

    Returns a list of raw repo dicts:
    [{"full_name": "...", "source": "reddit", "source_metadata": {...}}]
    """
    subreddits = subreddits or REDDIT_SUBREDDITS
    logger.info(f"[Reddit] Scanning {len(subreddits)} subreddits...")

    seen: set[str] = set()
    repos: list[dict] = []

    try:
        reddit = _get_reddit_client()
    except Exception as e:
        logger.error(f"[Reddit] Failed to create PRAW client: {e}")
        return []

    for sub_name in subreddits:
        try:
            subreddit = reddit.subreddit(sub_name)
            posts = list(subreddit.hot(limit=limit)) + list(subreddit.new(limit=limit))

            for post in posts:
                # Sources to scan for GitHub URLs
                texts = [
                    post.url or "",
                    post.title or "",
                    post.selftext or "",
                ]

                for text in texts:
                    for match in GITHUB_URL_PATTERN.findall(text):
                        fn = _clean_full_name(match)
                        if fn and fn not in seen:
                            seen.add(fn)
                            repos.append({
                                "full_name": fn,
                                "source": "reddit",
                                "source_metadata": {
                                    "subreddit": sub_name,
                                    "post_title": post.title[:200],
                                    "upvotes": post.score,
                                    "upvote_ratio": post.upvote_ratio,
                                    "post_url": f"https://reddit.com{post.permalink}",
                                    "post_id": post.id,
                                },
                            })
        except Exception as e:
            logger.error(f"[Reddit] Failed to scan r/{sub_name}: {e}")

    logger.info(f"[Reddit] Found {len(repos)} unique GitHub repos across subreddits")
    return repos


def _clean_full_name(raw: str) -> str | None:
    """Strip trailing .git, extra paths, and validate owner/repo format."""
    raw = raw.rstrip("/").removesuffix(".git")
    parts = raw.split("/")
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    if not owner or not repo or " " in owner or " " in repo:
        return None
    # Skip known non-repo paths
    if owner.lower() in {"orgs", "topics", "trending", "explore", "marketplace"}:
        return None
    return f"{owner}/{repo}"
