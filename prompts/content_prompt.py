"""
prompts/content_prompt.py — LLM prompts for the content generator agent (Claude Opus).
"""

CONTENT_SYSTEM_PROMPT = """You are a viral tech content creator for Instagram who specializes in developer tools and open-source software. Your audience is software engineers aged 20–35 who follow tech trends.

Your content is punchy, specific, and drops jargon-free technical insight in a way that makes engineers excited to try new tools.

CRITICAL RULES:
- Respond ONLY with valid JSON. No markdown, no prose, no code fences.
- reel_script must be ~150 words total, structured with clear section labels.
- Scores must be integers 0–100.
- Be specific — name real competitors, real use cases, real architecture choices.
"""

CONTENT_JSON_SCHEMA = {
    "reel_script": (
        "string — ~150 words total. MUST follow this exact structure:\n"
        "HOOK: [1-2 punchy sentences that stop the scroll]\n"
        "PROBLEM: [What pain this solves — be specific]\n"
        "SOLUTION: [What the repo does and how — keep it simple]\n"
        "WHY IT MATTERS: [Why devs should care right now]\n"
        "CTA: [Call to action — e.g. 'Link in bio. Go star it.']\n"
        "Each section on its own line."
    ),
    "creator_notes": (
        "string — filming/editing instructions:\n"
        "- What to show on screen during each section (terminal demo, code, diagrams?)\n"
        "- B-roll ideas\n"
        "- Text overlays to use\n"
        "- Suggested music vibe"
    ),
    "technical_breakdown": (
        "string — a detailed technical explainer including:\n"
        "- Architecture and key design decisions\n"
        "- Full tech stack\n"
        "- Top 3 pros and top 3 cons\n"
        "- Top 3 direct competitors and how this compares"
    ),
    "virality_score": "integer 0–100 — how likely is this to go viral on Instagram? (high = broad appeal, novel demo)",
    "learning_score": "integer 0–100 — how much will devs learn from this content? (high = teaches a new concept or pattern)",
    "innovation_score": "integer 0–100 — how innovative is the underlying project? (high = genuinely novel approach)",
    "score_reasoning": "string — 2–3 sentences explaining why you gave these scores",
}


def build_content_prompt(repo: dict, research: dict) -> str:
    """
    Build the user message for the content generator agent.

    repo: dict with keys full_name, url, stars_current, velocity_score, source, language
    research: dict from research agent (problem_solved, why_interesting, etc.)
    """
    topics_str = ", ".join(repo.get("topics") or []) or "none"
    alternatives_str = ", ".join(research.get("alternatives") or []) or "none identified"
    tech_stack_str = ", ".join(research.get("tech_stack") or []) or "not specified"
    pros_str = "\n".join(f"  + {p}" for p in (research.get("pros") or []))
    cons_str = "\n".join(f"  - {c}" for c in (research.get("cons") or []))

    return f"""Generate viral Instagram Reel content for this open-source repository.

REPOSITORY:
- Name: {repo.get("full_name", "unknown")}
- URL: {repo.get("url", "")}
- Stars: {repo.get("stars_current", 0):,}
- Velocity Score: {repo.get("velocity_score", 0.0):.1f} (stars gained per 100 total in last 24h)
- Source discovered: {repo.get("source", "unknown")}
- Language: {repo.get("language", "Unknown")}
- Topics: {topics_str}

RESEARCH FINDINGS:
- Problem solved: {research.get("problem_solved", "")}
- Why built: {research.get("why_built", "")}
- Target audience: {research.get("target_audience", "")}
- What makes it interesting: {research.get("why_interesting", "")}
- Architecture: {research.get("architecture_summary", "")}
- Tech stack: {tech_stack_str}
- Alternatives: {alternatives_str}
- Pros:
{pros_str}
- Cons:
{cons_str}

Return a JSON object with EXACTLY these keys:
{_format_schema(CONTENT_JSON_SCHEMA)}
"""


def _format_schema(schema: dict) -> str:
    lines = []
    for key, description in schema.items():
        lines.append(f'  "{key}": {description}')
    return "{\n" + ",\n".join(lines) + "\n}"
