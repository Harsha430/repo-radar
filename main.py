"""
main.py — RepoRadar LangGraph orchestrator (entry point).

Pipeline:
  discovery → filter → research → generate_content → save_run → send_whatsapp

Run locally:
  python main.py

Triggered automatically via GitHub Actions at 6 AM IST (00:30 UTC).
"""

import logging
import time
from datetime import date, datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from agents.discovery_agent import run_discovery
from agents.filter_agent import run_filter
from agents.generator_agent import run_generator
from agents.research_agent import run_research
from core.whatsapp_client import format_report, format_empty_report, send_whatsapp
from db.supabase_client import create_daily_run, update_daily_run

# ─── Logging Setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Pipeline State ───────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    run_id: str                          # Supabase daily_runs UUID
    raw_repos: list[dict]                # After discovery
    filtered_repos: list[dict]           # After filter
    researched_repos: list[dict]         # After research
    selected_repos: list[dict]           # After content selection
    generated_content: list[dict]        # Content records
    errors: list[str]                    # Non-fatal error log


# ─── Save Run Node ────────────────────────────────────────────────────────────

def save_run(state: PipelineState) -> PipelineState:
    """
    LangGraph node — updates the daily_runs record with final stats.
    This runs after content generation, before sending WhatsApp.
    """
    run_id = state.get("run_id", "")
    selected = state.get("selected_repos", [])
    generated = state.get("generated_content", [])
    errors = state.get("errors", [])

    if run_id:
        selected_ids = [r.get("id") for r in selected if r.get("id")]
        update_daily_run(run_id, {
            "discovered_count": len(state.get("raw_repos", [])),
            "after_filter_count": len(state.get("filtered_repos", [])),
            "researched_count": len(state.get("researched_repos", [])),
            "content_generated": len(generated),
            "selected_repo_ids": selected_ids,
            "error_log": "\n".join(errors) if errors else None,
            "status": "failed" if not generated and errors else "success",
        })

    logger.info("[Pipeline] Run record saved to Supabase.")
    return state


# ─── Send WhatsApp Node ───────────────────────────────────────────────────────

def send_report(state: PipelineState) -> PipelineState:
    """
    LangGraph node — formats and sends the WhatsApp report.
    Never fails the pipeline (errors are logged only).
    """
    selected = state.get("selected_repos", [])
    generated = state.get("generated_content", [])
    run_id = state.get("run_id", "")

    if selected and generated:
        message = format_report(selected, generated)
    else:
        message = format_empty_report()
        logger.warning("[Pipeline] Sending empty-run report — no content generated today.")

    success = send_whatsapp(message)

    if run_id:
        update_daily_run(run_id, {"whatsapp_sent": success})

    logger.info(f"[Pipeline] WhatsApp send: {'✓' if success else '✗'}")
    return state


# ─── Build LangGraph Pipeline ─────────────────────────────────────────────────

def build_pipeline() -> Any:
    graph = StateGraph(PipelineState)

    graph.add_node("discovery", run_discovery)
    graph.add_node("filter", run_filter)
    graph.add_node("research", run_research)
    graph.add_node("generate_content", run_generator)
    graph.add_node("save_run", save_run)
    graph.add_node("send_whatsapp", send_report)

    graph.set_entry_point("discovery")
    graph.add_edge("discovery", "filter")
    graph.add_edge("filter", "research")
    graph.add_edge("research", "generate_content")
    graph.add_edge("generate_content", "save_run")
    graph.add_edge("save_run", "send_whatsapp")
    graph.add_edge("send_whatsapp", END)

    return graph.compile()


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def main() -> None:
    start_time = time.time()
    today = date.today()

    logger.info("=" * 60)
    logger.info(f"  🔭 RepoRadar Pipeline Starting — {today.isoformat()}")
    logger.info("=" * 60)

    # Create daily_run record (idempotent via UNIQUE on run_date)
    run_id = create_daily_run(today) or ""
    if run_id:
        logger.info(f"[Pipeline] Daily run ID: {run_id}")
    else:
        logger.warning("[Pipeline] Could not create daily_run record — continuing anyway.")

    initial_state: PipelineState = {
        "run_id": run_id,
        "raw_repos": [],
        "filtered_repos": [],
        "researched_repos": [],
        "selected_repos": [],
        "generated_content": [],
        "errors": [],
    }

    pipeline = build_pipeline()

    try:
        final_state = pipeline.invoke(initial_state)
    except Exception as e:
        logger.critical(f"[Pipeline] FATAL: Pipeline crashed: {e}", exc_info=True)
        if run_id:
            update_daily_run(run_id, {
                "status": "failed",
                "error_log": str(e),
            })
        # Try to send a failure WhatsApp notification
        send_whatsapp(f"🔭 *RepoRadar* — Pipeline FAILED ❌\n\nError: {e}")
        raise

    elapsed = int(time.time() - start_time)

    # Update duration
    if run_id:
        update_daily_run(run_id, {"duration_seconds": elapsed})

    # ── Summary ────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("  ✅ RepoRadar Pipeline Complete")
    logger.info(f"  Duration: {elapsed}s")
    logger.info(f"  Discovered:       {len(final_state.get('raw_repos', []))}")
    logger.info(f"  After filter:     {len(final_state.get('filtered_repos', []))}")
    logger.info(f"  Researched:       {len(final_state.get('researched_repos', []))}")
    logger.info(f"  Content generated:{len(final_state.get('generated_content', []))}")

    selected = final_state.get("selected_repos", [])
    if selected:
        logger.info("")
        logger.info("  📦 Selected Repos:")
        for r in selected:
            logger.info(
                f"    • {r.get('full_name')} | "
                f"⭐ {r.get('stars_current', 0):,} | "
                f"⚡ {r.get('velocity_score', 0):.1f}"
            )

    errors = final_state.get("errors", [])
    if errors:
        logger.info("")
        logger.info(f"  ⚠️  Non-fatal errors ({len(errors)}):")
        for err in errors[:5]:
            logger.info(f"    {err}")

    logger.info("=" * 60)


if __name__ == "__main__":
    main()
