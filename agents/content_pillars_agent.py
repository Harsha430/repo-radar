"""
agents/content_pillars_agent.py — Generates one rotating pillar content post per day.
LangGraph node: run_content_pillars(state) → state with pillar_content list.

Daily schedule (from settings.py):
  Monday    → problem_solution
  Tuesday   → hidden_problem
  Wednesday → comparison
  Thursday  → workflow
  Friday    → hidden_problem
  Saturday  → roadmap
  Sunday    → trend_report (uses real Supabase data — no hallucination)

Theme selection enforces a 28-day no-repeat window per pillar.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from config.settings import (
    CONTENT_MODEL,
    CONTENT_PROVIDER,
    DAILY_PILLAR_SCHEDULE,
    WORKFLOW_THEMES,
    ROADMAP_THEMES,
    COMPARISON_TOPICS,
    PROBLEM_TOPICS,
    PROBLEM_SOLUTION_THEMES,
)
from core.llm_client import chat as llm_chat
from db.supabase_client import (
    insert_pillar_content,
    get_used_pillar_themes,
    get_weekly_repo_summary,
)
from prompts.pillar_prompts import (
    PILLAR_SYSTEM_PROMPT,
    build_workflow_prompt,
    build_roadmap_prompt,
    build_comparison_prompt,
    build_problem_solution_prompt,
    build_hidden_problem_prompt,
    build_trend_report_prompt,
)

logger = logging.getLogger(__name__)


# ─── Main Node ────────────────────────────────────────────────────────────────

def run_content_pillars(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — generates today's pillar content.
    Checks the day of week, picks the right pillar, selects an unused theme,
    generates content via LLM, saves to Supabase, and returns in state.
    """
    errors: list[str] = list(state.get("errors", []))

    try:
        day_of_week = datetime.now(timezone.utc).weekday()
        pillar = DAILY_PILLAR_SCHEDULE.get(day_of_week, "workflow")
        logger.info(f"[Pillars] Today is weekday {day_of_week} → pillar: {pillar}")

        # Pick theme (with 28-day dedup)
        theme, theme_key = _pick_theme(pillar)
        if theme is None:
            logger.warning(f"[Pillars] All themes exhausted for pillar '{pillar}' — skipping.")
            return {**state, "pillar_content": [], "errors": errors}

        logger.info(f"[Pillars] Selected theme: '{theme}'")

        # Build the user prompt
        user_prompt = _build_user_prompt(pillar, theme, theme_key)

        # Call LLM
        raw_text = llm_chat(
            model=CONTENT_MODEL,
            system=PILLAR_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=4000,
            provider=CONTENT_PROVIDER,
        )

        # Parse JSON
        parsed = _parse_json(raw_text, pillar)
        if parsed is None:
            errors.append(f"pillars:json_parse_failed:{pillar}:{theme}")
            return {**state, "pillar_content": [], "errors": errors}

        # Build record
        record = {
            "pillar": pillar,
            "theme": theme,
            "hook": parsed.get("hook", ""),
            "slides": parsed.get("slides", []),
            "caption": parsed.get("caption", ""),
            "virality_score": int(parsed.get("virality_score", 0)),
            "posted": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save to Supabase
        pillar_id = insert_pillar_content(record)
        logger.info(f"[Pillars] Saved pillar content (id={pillar_id}) for '{theme}'")

        return {
            **state,
            "pillar_content": [{**record, "id": pillar_id}],
            "errors": errors,
        }

    except Exception as e:
        msg = f"[Pillars] Fatal error in content_pillars_agent: {e}"
        logger.error(msg, exc_info=True)
        errors.append(msg)
        return {**state, "pillar_content": [], "errors": errors}


# ─── Theme Selection ──────────────────────────────────────────────────────────

def _pick_theme(pillar: str) -> tuple[Any, Any]:
    """
    Pick a fresh theme for the given pillar that hasn't been used in the last 28 days.
    Returns (theme_display_string, theme_key) where theme_key is used internally.
    For comparison: theme_key is (tool_a, tool_b) tuple.
    For hidden_problem: theme_key is (language, topic) tuple.
    For others: theme_key == theme_display_string.
    """
    used = set(get_used_pillar_themes(pillar, days=28))

    if pillar == "workflow":
        candidates = WORKFLOW_THEMES
        for t in candidates:
            if t not in used:
                return t, t
        # All exhausted — start over from the beginning
        return WORKFLOW_THEMES[0], WORKFLOW_THEMES[0]

    elif pillar == "roadmap":
        candidates = ROADMAP_THEMES
        for t in candidates:
            if t not in used:
                return t, t
        return ROADMAP_THEMES[0], ROADMAP_THEMES[0]

    elif pillar == "comparison":
        for pair in COMPARISON_TOPICS:
            tool_a, tool_b = pair
            theme_str = f"{tool_a} vs {tool_b}"
            if theme_str not in used:
                return theme_str, pair
        pair = COMPARISON_TOPICS[0]
        return f"{pair[0]} vs {pair[1]}", pair

    elif pillar == "problem_solution":
        for t in PROBLEM_SOLUTION_THEMES:
            if t not in used:
                return t, t
        return PROBLEM_SOLUTION_THEMES[0], PROBLEM_SOLUTION_THEMES[0]

    elif pillar == "hidden_problem":
        for pair in PROBLEM_TOPICS:
            lang, topic = pair
            theme_str = f"{lang}: {topic}"
            if theme_str not in used:
                return theme_str, pair
        pair = PROBLEM_TOPICS[0]
        return f"{pair[0]}: {pair[1]}", pair

    elif pillar == "trend_report":
        # Trend reports always run — theme is the current week label
        week = datetime.now(timezone.utc).strftime("Week of %Y-%m-%d")
        return week, week

    return None, None


# ─── Prompt Dispatch ──────────────────────────────────────────────────────────

def _build_user_prompt(pillar: str, theme: str, theme_key: Any) -> str:
    """Route to the correct prompt builder based on pillar type."""
    if pillar == "workflow":
        return build_workflow_prompt(theme)

    elif pillar == "roadmap":
        return build_roadmap_prompt(theme)

    elif pillar == "comparison":
        tool_a, tool_b = theme_key  # theme_key is a tuple for comparisons
        return build_comparison_prompt(tool_a, tool_b)

    elif pillar == "problem_solution":
        return build_problem_solution_prompt(theme)

    elif pillar == "hidden_problem":
        language, topic = theme_key  # theme_key is a tuple for hidden_problem
        return build_hidden_problem_prompt(language, topic)

    elif pillar == "trend_report":
        weekly_data = get_weekly_repo_summary()
        logger.info(f"[Pillars] Trend Report: fetched {len(weekly_data)} repos from last 7 days")
        return build_trend_report_prompt(weekly_data)

    raise ValueError(f"Unknown pillar: {pillar}")


# ─── JSON Parser ──────────────────────────────────────────────────────────────

def _parse_json(text: str, context: str = "") -> dict | None:
    """Parse JSON from LLM response with basic cleanup."""
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError as e:
        logger.error(f"[Pillars] JSON parse error for {context}: {e}\nRaw: {text[:400]}")
        return None
