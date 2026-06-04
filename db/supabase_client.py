"""
db/supabase_client.py — Typed helper functions for all Supabase read/write operations.
"""

import logging
from datetime import date, datetime, timezone
from typing import Any

from supabase import create_client, Client

from config.settings import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

# ─── Client Singleton ─────────────────────────────────────────────────────────

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ─── Repos ───────────────────────────────────────────────────────────────────

def get_seen_github_ids() -> set[int]:
    """Return all github_ids ever stored — used for deduplication."""
    try:
        client = get_client()
        response = client.table("repos").select("github_id").execute()
        return {row["github_id"] for row in response.data}
    except Exception as e:
        logger.error(f"[Supabase] Failed to fetch seen github_ids: {e}")
        return set()


def upsert_repo(repo: dict[str, Any]) -> str | None:
    """
    Insert or update a repo row.
    Returns the UUID of the row, or None on failure.
    """
    try:
        client = get_client()
        response = (
            client.table("repos")
            .upsert(repo, on_conflict="github_id")
            .execute()
        )
        if response.data:
            return response.data[0]["id"]
        return None
    except Exception as e:
        logger.error(f"[Supabase] Failed to upsert repo {repo.get('full_name')}: {e}")
        return None


def mark_repo_filtered(repo_id: str, passed: bool, reason: str | None = None) -> None:
    """Update the passed_filter and filter_reason fields for a repo."""
    try:
        client = get_client()
        client.table("repos").update(
            {"passed_filter": passed, "filter_reason": reason, "last_checked_at": _now()}
        ).eq("id", repo_id).execute()
    except Exception as e:
        logger.error(f"[Supabase] Failed to mark filter for repo {repo_id}: {e}")


# ─── Research ─────────────────────────────────────────────────────────────────

def insert_research(research: dict[str, Any]) -> str | None:
    """
    Insert a research row.
    Returns the UUID, or None on failure.
    """
    try:
        client = get_client()
        response = client.table("research").insert(research).execute()
        if response.data:
            return response.data[0]["id"]
        return None
    except Exception as e:
        logger.error(f"[Supabase] Failed to insert research for repo {research.get('repo_id')}: {e}")
        return None


# ─── Content ──────────────────────────────────────────────────────────────────

def insert_content(content: dict[str, Any]) -> str | None:
    """
    Insert a content row.
    Returns the UUID, or None on failure.
    """
    try:
        client = get_client()
        response = client.table("content").insert(content).execute()
        if response.data:
            return response.data[0]["id"]
        return None
    except Exception as e:
        logger.error(f"[Supabase] Failed to insert content for repo {content.get('repo_id')}: {e}")
        return None


# ─── Daily Runs ───────────────────────────────────────────────────────────────

def create_daily_run(run_date: date | None = None) -> str | None:
    """
    Create a new daily_run row with status='running'.
    Returns the UUID, or None on failure.
    """
    try:
        client = get_client()
        today = (run_date or date.today()).isoformat()
        response = (
            client.table("daily_runs")
            .upsert({"run_date": today, "status": "running"}, on_conflict="run_date")
            .execute()
        )
        if response.data:
            return response.data[0]["id"]
        return None
    except Exception as e:
        logger.error(f"[Supabase] Failed to create daily_run: {e}")
        return None


def update_daily_run(run_id: str, fields: dict[str, Any]) -> None:
    """Patch any fields on a daily_run row."""
    try:
        client = get_client()
        client.table("daily_runs").update(fields).eq("id", run_id).execute()
    except Exception as e:
        logger.error(f"[Supabase] Failed to update daily_run {run_id}: {e}")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
