"""
core/github_client.py — GitHub REST API client with trending scrape, search, velocity
computation, and rate-limit-aware retry logic.
"""

import base64
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from config.settings import (
    GH_PAT,
    GITHUB_SEARCH_QUERIES,
    GITHUB_RATE_LIMIT_RETRIES,
    STARGAZER_PAGE_SIZE,
    STARS_MIN,
    STARS_MAX,
    REPO_AGE_MIN_DAYS,
    REPO_AGE_MAX_DAYS,
    README_MIN_LENGTH,
)

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GH_PAT}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
STAR_TIMESTAMP_HEADERS = {
    **HEADERS,
    "Accept": "application/vnd.github.v3.star+json",
}


# ─── Rate Limit Retry ─────────────────────────────────────────────────────────

def _request(method: str, url: str, **kwargs) -> requests.Response:
    """Make a GitHub API request with automatic rate-limit retry."""
    for attempt in range(1, GITHUB_RATE_LIMIT_RETRIES + 1):
        resp = requests.request(method, url, headers=HEADERS, timeout=30, **kwargs)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset_ts = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset_ts - int(time.time()), 5)
            logger.warning(f"[GitHub] Rate limited. Sleeping {wait}s (attempt {attempt}/{GITHUB_RATE_LIMIT_RETRIES})")
            time.sleep(wait)
            continue
        return resp
    resp.raise_for_status()
    return resp


def _star_request(url: str, **kwargs) -> requests.Response:
    """Same as _request but uses the star-timestamp Accept header."""
    for attempt in range(1, GITHUB_RATE_LIMIT_RETRIES + 1):
        resp = requests.get(url, headers=STAR_TIMESTAMP_HEADERS, timeout=30, **kwargs)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset_ts = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset_ts - int(time.time()), 5)
            logger.warning(f"[GitHub] Rate limited (stargazers). Sleeping {wait}s")
            time.sleep(wait)
            continue
        return resp
    return resp


# ─── Trending Scraper ─────────────────────────────────────────────────────────

def get_trending_repos() -> list[dict]:
    """Scrape GitHub Trending page and return a list of raw repo dicts."""
    logger.info("[GitHub] Fetching trending repos...")
    repos = []
    try:
        resp = requests.get(
            "https://github.com/trending",
            headers={"User-Agent": "RepoRadar/1.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        articles = soup.find_all("article", class_="Box-row")

        for article in articles:
            try:
                h2 = article.find("h2")
                if not h2:
                    continue
                link = h2.find("a")
                if not link:
                    continue
                full_name = link["href"].strip("/")
                repos.append({"full_name": full_name, "source": "github_trending"})
            except Exception as e:
                logger.debug(f"[GitHub] Trending parse error: {e}")
    except Exception as e:
        logger.error(f"[GitHub] Trending scrape failed: {e}")
    logger.info(f"[GitHub] Trending: found {len(repos)} repos")
    return repos


# ─── Search API ───────────────────────────────────────────────────────────────

def search_github_repos() -> list[dict]:
    """Run all curated search queries and return a deduplicated list of raw repo dicts."""
    logger.info("[GitHub] Running search queries...")
    seen: set[str] = set()
    repos: list[dict] = []

    for query in GITHUB_SEARCH_QUERIES:
        try:
            resp = _request(
                "GET",
                f"{GITHUB_API}/search/repositories",
                params={"q": query, "per_page": 30, "sort": "updated"},
            )
            if resp.status_code != 200:
                logger.warning(f"[GitHub] Search query failed ({resp.status_code}): {query}")
                continue
            items = resp.json().get("items", [])
            for item in items:
                fn = item.get("full_name", "")
                if fn and fn not in seen:
                    seen.add(fn)
                    repos.append({"full_name": fn, "source": "github_search"})
        except Exception as e:
            logger.error(f"[GitHub] Search query error for '{query}': {e}")

    logger.info(f"[GitHub] Search: found {len(repos)} unique repos")
    return repos


# ─── Repo Metadata ────────────────────────────────────────────────────────────

def get_repo_metadata(full_name: str) -> dict[str, Any] | None:
    """
    Fetch full repo metadata from the GitHub REST API.
    Returns a structured dict or None on failure.
    """
    try:
        resp = _request("GET", f"{GITHUB_API}/repos/{full_name}")
        if resp.status_code == 404:
            logger.debug(f"[GitHub] Repo not found: {full_name}")
            return None
        resp.raise_for_status()
        data = resp.json()

        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - created_at).days

        # Extract license name safely
        license_name = None
        if data.get("license") and isinstance(data["license"], dict):
            license_name = data["license"].get("spdx_id") or data["license"].get("name")

        return {
            "github_id": data["id"],
            "full_name": data["full_name"],
            "url": data["html_url"],
            "description": data.get("description"),
            "language": data.get("language"),
            "topics": data.get("topics", []),
            "license": license_name,
            "stars_current": data["stargazers_count"],
            "forks": data["forks_count"],
            "owner_login": data["owner"]["login"],
            "repo_age_days": age_days,
            "has_description": bool(data.get("description")),
        }
    except Exception as e:
        logger.error(f"[GitHub] Metadata fetch failed for {full_name}: {e}")
        return None


# ─── README Fetcher ───────────────────────────────────────────────────────────

def get_readme(full_name: str) -> str:
    """Fetch and decode the README for a repo. Returns empty string on failure."""
    try:
        resp = _request("GET", f"{GITHUB_API}/repos/{full_name}/readme")
        if resp.status_code != 200:
            return ""
        content = resp.json().get("content", "")
        encoding = resp.json().get("encoding", "base64")
        if encoding == "base64":
            return base64.b64decode(content).decode("utf-8", errors="replace")
        return content
    except Exception as e:
        logger.error(f"[GitHub] README fetch failed for {full_name}: {e}")
        return ""


# ─── Velocity Computation ─────────────────────────────────────────────────────

def compute_velocity(full_name: str, total_stars: int) -> tuple[float, int]:
    """
    Fetch the last N stargazers (with timestamps) and count how many starred
    within the last 24 hours. Returns (velocity_score, stars_gained_24h).

    velocity_score = (stars_gained_24h / max(total_stars, 1)) * 100
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    stars_gained_24h = 0

    try:
        # Fetch last page of stargazers (most recent) — one page of 100
        url = f"{GITHUB_API}/repos/{full_name}/stargazers"
        params = {"per_page": STARGAZER_PAGE_SIZE, "page": 1}

        # To get most recent, we need to find the last page
        # GitHub doesn't support sorting — we use the last page trick via Link header
        resp = _star_request(url, params=params)
        if resp.status_code != 200:
            return 0.0, 0

        # Determine total pages from Link header
        link_header = resp.headers.get("Link", "")
        last_page = _parse_last_page(link_header)

        if not last_page or last_page == 1:
            # Page 1 IS the only/last page — already have the data
            stargazers = resp.json()
        else:
            resp = _star_request(url, params={"per_page": STARGAZER_PAGE_SIZE, "page": last_page})
            if resp.status_code != 200:
                return 0.0, 0
            stargazers = resp.json()
        for sg in stargazers:
            starred_at_str = sg.get("starred_at", "")
            if not starred_at_str:
                continue
            starred_at = datetime.fromisoformat(starred_at_str.replace("Z", "+00:00"))
            if starred_at >= cutoff:
                stars_gained_24h += 1

    except Exception as e:
        logger.error(f"[GitHub] Velocity computation failed for {full_name}: {e}")
        return 0.0, 0

    velocity_score = (stars_gained_24h / max(total_stars, 1)) * 100
    return round(velocity_score, 4), stars_gained_24h


def _parse_last_page(link_header: str) -> int | None:
    """Extract the last page number from a GitHub Link header."""
    match = re.search(r'page=(\d+)>;\s*rel="last"', link_header)
    if match:
        return int(match.group(1))
    return None
