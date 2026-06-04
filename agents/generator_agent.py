"""
agents/generator_agent.py — Scores researched repos, selects top 1–3, generates content.
LangGraph node: run_generator(state) → state with selected_repos and generated_content.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import anthropic

from config.settings import (
    CONTENT_MODEL,
    CONTENT_PROVIDER,
    TOP_K_CONTENT,
    SCORE_WEIGHT_VIRALITY,
    SCORE_WEIGHT_LEARNING,
    SCORE_WEIGHT_INNOVATION,
)
from core.llm_client import chat as llm_chat
from db.supabase_client import insert_content
from prompts.content_prompt import CONTENT_SYSTEM_PROMPT, build_content_prompt

logger = logging.getLogger(__name__)


def run_generator(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node:
    1. Score each researched repo (velocity + research novelty heuristic)
    2. Select top 1–3
    3. Generate content for each via Claude Opus (parallel)
    4. Save to Supabase
    5. Return state with selected_repos and generated_content
    """
    researched_repos: list[dict] = state.get("researched_repos", [])
    errors: list[str] = list(state.get("errors", []))

    if not researched_repos:
        logger.warning("[Generator] No researched repos to generate content for.")
        return {**state, "selected_repos": [], "generated_content": [], "errors": errors}

    # ── Step 1: Score + select top K ─────────────────────────────────────────
    scored = [_score_repo(r) for r in researched_repos]
    scored.sort(key=lambda r: r["_selection_score"], reverse=True)
    selected = scored[:TOP_K_CONTENT]

    logger.info(
        f"[Generator] Selected {len(selected)} repos for content generation: "
        + ", ".join(r.get("full_name", "?") for r in selected)
    )

    # ── Step 2: Generate content in parallel ─────────────────────────────────
    generated: list[dict] = []

    def generate_one(repo: dict) -> dict | None:
        fn = repo.get("full_name", "unknown")
        research = repo.get("research", {})
        try:
            prompt = build_content_prompt(repo, research)
            raw_text = llm_chat(
                model=CONTENT_MODEL,
                system=CONTENT_SYSTEM_PROMPT,
                user=prompt,
                max_tokens=3000,
                provider=CONTENT_PROVIDER,
            )
            parsed = _parse_json(raw_text, fn)
            if parsed is None:
                errors.append(f"generator:json_parse_failed:{fn}")
                return None

            virality = int(parsed.get("virality_score", 0))
            learning = int(parsed.get("learning_score", 0))
            innovation = int(parsed.get("innovation_score", 0))
            overall = round(
                SCORE_WEIGHT_VIRALITY * virality
                + SCORE_WEIGHT_LEARNING * learning
                + SCORE_WEIGHT_INNOVATION * innovation,
                2,
            )

            content_record = {
                "repo_id": repo.get("id"),
                "research_id": repo.get("research_id"),
                "reel_script": parsed.get("reel_script", ""),
                "creator_notes": parsed.get("creator_notes", ""),
                "technical_breakdown": parsed.get("technical_breakdown", ""),
                "virality_score": virality,
                "learning_score": learning,
                "innovation_score": innovation,
                "overall_score": overall,
                "posted_to_instagram": False,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            content_id = insert_content(content_record)
            return {**content_record, "id": content_id}

        except Exception as e:
            msg = f"[Generator] Content generation failed for {fn}: {e}"
            logger.error(msg)
            errors.append(msg)
            return None

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(generate_one, r): r for r in selected}
        for future in as_completed(futures):
            result = future.result()
            if result:
                generated.append(result)

    logger.info(f"[Generator] Generated content for {len(generated)} repos")

    return {
        **state,
        "selected_repos": selected,
        "generated_content": generated,
        "errors": errors,
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _score_repo(repo: dict) -> dict:
    """
    Compute a composite selection score:
      velocity_score (normalized) × 0.5 + novelty_heuristic × 0.5

    novelty_heuristic is derived from research quality signals:
    - has why_interesting text (good)
    - has multiple alternatives (suggests real ecosystem = good)
    - many pros listed (= well-researched = good)
    """
    velocity = repo.get("velocity_score", 0.0)
    research = repo.get("research", {})

    novelty = 0.0
    if research.get("why_interesting"):
        novelty += 40.0
    if len(research.get("alternatives", [])) >= 2:
        novelty += 30.0
    if len(research.get("pros", [])) >= 3:
        novelty += 30.0

    selection_score = (min(velocity, 100.0) * 0.5) + (novelty * 0.5)
    return {**repo, "_selection_score": round(selection_score, 2)}


def _parse_json(text: str, context: str = "") -> dict | None:
    """Attempt to parse JSON from Claude's response, with basic cleanup."""
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError as e:
        logger.error(f"[Generator] JSON parse error for {context}: {e}\nRaw: {text[:300]}")
        return None
