"""
agents/research_agent.py — Deep per-repo research using Claude Opus in parallel.
LangGraph node: run_research(state) → state with researched_repos populated.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import anthropic

from config.settings import RESEARCH_MODEL
from core.github_client import get_readme, get_repo_metadata
from core.llm_client import chat as llm_chat
from db.supabase_client import insert_research
from prompts.research_prompt import RESEARCH_SYSTEM_PROMPT, build_research_prompt

logger = logging.getLogger(__name__)


def run_research(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — for each filtered repo, fetch README (if not cached) and run
    Claude Opus research. Saves results to Supabase. Rejects repos where
    is_real_project == false. Returns state with researched_repos populated.
    """
    filtered_repos: list[dict] = state.get("filtered_repos", [])
    errors: list[str] = list(state.get("errors", []))

    if not filtered_repos:
        logger.warning("[Research] No filtered repos to research.")
        return {**state, "researched_repos": [], "errors": errors}

    logger.info(f"[Research] Researching {len(filtered_repos)} repos with {RESEARCH_MODEL}...")

    def research_one(repo: dict) -> dict | None:
        fn = repo.get("full_name", "unknown")
        try:
            # Use cached README from filter stage if available, otherwise re-fetch
            readme = repo.get("_readme") or get_readme(fn)

            # Re-fetch metadata if github_id missing (edge case)
            if not repo.get("github_id"):
                meta = get_repo_metadata(fn)
                if meta:
                    repo = {**repo, **meta}

            prompt = build_research_prompt(repo, readme)

            raw_text = llm_chat(
                model=RESEARCH_MODEL,
                system=RESEARCH_SYSTEM_PROMPT,
                user=prompt,
                max_tokens=2000,
            )
            parsed = _parse_json(raw_text, fn)
            if parsed is None:
                errors.append(f"research:json_parse_failed:{fn}")
                return None

            # Reject if LLM says not a real project
            if not parsed.get("is_real_project", True):
                reason = parsed.get("rejection_reason", "LLM flagged as not real project")
                logger.info(f"[Research] Rejected {fn}: {reason}")
                return None

            # Save to Supabase
            research_record = {
                "repo_id": repo.get("id"),
                "problem_solved": parsed.get("problem_solved"),
                "why_built": parsed.get("why_built"),
                "target_audience": parsed.get("target_audience"),
                "alternatives": parsed.get("alternatives", []),
                "why_interesting": parsed.get("why_interesting"),
                "architecture_summary": parsed.get("architecture_summary"),
                "tech_stack": parsed.get("tech_stack", []),
                "pros": parsed.get("pros", []),
                "cons": parsed.get("cons", []),
                "raw_readme": readme[:10000],  # Cap storage at 10k chars
                "raw_llm_response": parsed,
                "researched_at": datetime.now(timezone.utc).isoformat(),
            }
            research_id = insert_research(research_record)

            return {
                **repo,
                "research": parsed,
                "research_id": research_id,
            }

        except Exception as e:
            msg = f"[Research] Failed for {fn}: {e}"
            logger.error(msg)
            errors.append(msg)
            return None

    researched: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(research_one, r): r for r in filtered_repos}
        for future in as_completed(futures):
            result = future.result()
            if result:
                researched.append(result)

    logger.info(f"[Research] {len(researched)}/{len(filtered_repos)} repos successfully researched")

    return {
        **state,
        "researched_repos": researched,
        "errors": errors,
    }


def _parse_json(text: str, context: str = "") -> dict | None:
    """Attempt to parse JSON from Claude's response, with basic cleanup."""
    # Strip markdown code fences if Claude disobeys instructions
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"[Research] JSON parse error for {context}: {e}\nRaw: {text[:300]}")
        return None
