"""
agents/filter_agent.py — Applies hard rules and LLM quality check to raw repos.
LangGraph node: run_filter(state) → state with filtered_repos (top 8 by velocity).

Strategy (per implementation plan):
  1. Apply cheap hard rules (no API cost) — drops most repos
  2. For survivors: fetch GitHub metadata + compute velocity
  3. Apply velocity threshold
  4. Run claude-haiku-4-5 LLM quality check in parallel on survivors
  5. Sort by velocity, keep top 8
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import anthropic

from config.settings import (
    FILTER_MODEL,
    VELOCITY_THRESHOLD,
    STARS_MIN,
    STARS_MAX,
    REPO_AGE_MIN_DAYS,
    REPO_AGE_MAX_DAYS,
    README_MIN_LENGTH,
    TOP_K_AFTER_FILTER,
)
from core.github_client import get_repo_metadata, get_readme, compute_velocity
from core.llm_client import chat as llm_chat
from db.supabase_client import get_seen_github_ids, upsert_repo, mark_repo_filtered

logger = logging.getLogger(__name__)

FILTER_SYSTEM_PROMPT = """You are a quality gate for open-source repositories. You will receive basic info about a GitHub repo. Respond ONLY with valid JSON.

Reject the repo (is_acceptable: false) if ANY of these are true:
- It's a toy, demo, tutorial, or hello-world project
- It's a fork with no meaningful changes
- It appears abandoned (no commits in 6+ months, no issues)
- It has no real-world use case (purely academic or experimental)
- It's a copy/clone of a well-known project

Otherwise, approve it (is_acceptable: true).
"""


def run_filter(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — filters raw_repos through hard rules, velocity, and LLM check.
    Saves all repos to Supabase (with pass/fail status) before returning.
    """
    raw_repos: list[dict] = state.get("raw_repos", [])
    errors: list[str] = list(state.get("errors", []))

    if not raw_repos:
        logger.warning("[Filter] No raw repos to filter.")
        return {**state, "filtered_repos": [], "errors": errors}

    # ── Step 1: Dedup against Supabase (repos seen on previous days) ──────────
    seen_ids = get_seen_github_ids()
    logger.info(f"[Filter] {len(seen_ids)} github_ids already seen in DB. Deduping {len(raw_repos)} raw repos...")

    # ── Step 2: Fetch metadata + apply cheap hard rules (parallel) ────────────
    candidates: list[dict] = []

    def fetch_and_precheck(raw: dict) -> dict | None:
        """Fetch metadata, apply hard rules, return enriched dict or None."""
        fn = raw.get("full_name", "")
        try:
            meta = get_repo_metadata(fn)
            if not meta:
                return None

            # Dedup against existing DB records
            if meta["github_id"] in seen_ids:
                logger.debug(f"[Filter] Skip {fn} — already seen (github_id in DB)")
                return None

            # Hard rule: stars range
            stars = meta["stars_current"]
            if stars < STARS_MIN or stars > STARS_MAX:
                _save_rejected(meta, raw, f"stars out of range: {stars}")
                return None

            # Hard rule: repo age
            age = meta["repo_age_days"]
            if age < REPO_AGE_MIN_DAYS or age > REPO_AGE_MAX_DAYS:
                _save_rejected(meta, raw, f"age out of range: {age} days")
                return None

            # Hard rule: must have description
            if not meta.get("description"):
                _save_rejected(meta, raw, "no description")
                return None

            # Fetch README
            readme = get_readme(fn)
            if len(readme) < README_MIN_LENGTH:
                _save_rejected(meta, raw, f"README too short ({len(readme)} chars)")
                return None

            # Compute velocity ONLY for repos that passed cheap rules
            velocity, gained_24h = compute_velocity(fn, stars)

            # Hard rule: velocity threshold
            if velocity < VELOCITY_THRESHOLD:
                merged = {**meta, **raw, "velocity_score": velocity, "stars_gained_24h": gained_24h}
                _save_rejected(merged, raw, f"velocity too low: {velocity:.2f}")
                return None

            return {
                **meta,
                "source": raw.get("source", "unknown"),
                "source_metadata": raw.get("source_metadata"),
                "velocity_score": velocity,
                "stars_gained_24h": gained_24h,
                "stars_at_discovery": stars,
                "_readme": readme,  # carry for research agent
            }

        except Exception as e:
            logger.error(f"[Filter] Error processing {fn}: {e}")
            errors.append(f"filter_precheck:{fn}:{e}")
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_and_precheck, r): r for r in raw_repos}
        for future in as_completed(futures):
            result = future.result()
            if result:
                candidates.append(result)

    logger.info(f"[Filter] {len(candidates)} repos passed hard rules + velocity check")

    if not candidates:
        return {**state, "filtered_repos": [], "errors": errors}

    # ── Step 3: LLM quality check (parallel, claude-haiku) ───────────────────
    def llm_quality_check(repo: dict) -> dict | None:
        """Run Haiku quality check. Returns repo dict if acceptable, None if rejected."""
        fn = repo.get("full_name", "")
        try:
            prompt = (
                f"Repo: {fn}\n"
                f"Description: {repo.get('description', '')}\n"
                f"Language: {repo.get('language', 'unknown')}\n"
                f"Stars: {repo.get('stars_current', 0)}\n"
                f"Age: {repo.get('repo_age_days', 0)} days\n"
                f"Topics: {', '.join(repo.get('topics') or [])}\n"
                f"README snippet: {repo.get('_readme', '')[:500]}"
            )
            text = llm_chat(
                model=FILTER_MODEL,
                system=FILTER_SYSTEM_PROMPT,
                user=prompt,
                max_tokens=200,
            )
            parsed = json.loads(text)

            if parsed.get("is_acceptable", True):
                return repo
            else:
                reason = parsed.get("rejection_reason", "LLM quality check failed")
                _save_rejected(repo, repo, f"LLM: {reason}")
                return None
        except Exception as e:
            logger.error(f"[Filter] LLM quality check failed for {fn}: {e}")
            errors.append(f"filter_llm:{fn}:{e}")
            # On LLM failure, let the repo pass (don't penalize for API errors)
            return repo

    passed: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(llm_quality_check, r): r for r in candidates}
        for future in as_completed(futures):
            result = future.result()
            if result:
                passed.append(result)

    logger.info(f"[Filter] {len(passed)} repos passed LLM quality check")

    # ── Step 4: Sort by velocity, keep top K, save to Supabase ───────────────
    passed.sort(key=lambda r: r.get("velocity_score", 0), reverse=True)
    top_k = passed[:TOP_K_AFTER_FILTER]

    for repo in top_k:
        db_id = upsert_repo(_to_db_dict(repo))
        if db_id:
            repo["id"] = db_id
            mark_repo_filtered(db_id, passed=True)

    logger.info(f"[Filter] Final: {len(top_k)} repos selected (top {TOP_K_AFTER_FILTER} by velocity)")

    return {
        **state,
        "filtered_repos": top_k,
        "errors": errors,
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _save_rejected(meta: dict, raw: dict, reason: str) -> None:
    """Upsert a rejected repo to Supabase and mark it as failed filter."""
    try:
        db_dict = _to_db_dict({**meta, "source": raw.get("source", "unknown"),
                                "source_metadata": raw.get("source_metadata")})
        db_id = upsert_repo(db_dict)
        if db_id:
            mark_repo_filtered(db_id, passed=False, reason=reason)
    except Exception as e:
        logger.warning(f"[Filter] Could not save rejected repo to DB ({reason}): {e}")


def _to_db_dict(repo: dict) -> dict:
    """Map enriched repo dict to Supabase repos table schema."""
    return {
        "github_id": repo.get("github_id"),
        "full_name": repo.get("full_name"),
        "url": repo.get("url"),
        "description": repo.get("description"),
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "license": repo.get("license"),
        "stars_at_discovery": repo.get("stars_at_discovery", repo.get("stars_current")),
        "stars_current": repo.get("stars_current"),
        "forks": repo.get("forks"),
        "velocity_score": repo.get("velocity_score"),
        "stars_gained_24h": repo.get("stars_gained_24h"),
        "source": repo.get("source"),
        "source_metadata": repo.get("source_metadata"),
        "owner_login": repo.get("owner_login"),
        "repo_age_days": repo.get("repo_age_days"),
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
    }
