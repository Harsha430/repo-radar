"""
prompts/pillar_prompts.py — LLM prompt builders for the 6 content pillars.

Each builder returns (system_prompt, user_prompt) and expects the LLM to
respond with a JSON object:
  {
    "hook":          string,
    "reel_script":   string,
    "caption":       string,
    "virality_score": int 0-100
  }
"""

# ─── Shared system prompt ─────────────────────────────────────────────────────

PILLAR_SYSTEM_PROMPT = """You are a viral tech content creator for Instagram Reels targeting software engineers aged 20-35.

Your content is:
- Punchy, specific, and technically credible
- Jargon-free but never dumbed-down
- Immediately actionable — devs should be able to use what they learn TODAY
- Original — never generic advice, always concrete examples
- Formatted as a spoken script for a short-form video (30-60 seconds)

CRITICAL OUTPUT RULES:
- Respond ONLY with valid JSON. No markdown fences, no prose, no extra text.
- "reel_script" must be a spoken script. Include visual cues in brackets like [Show code snippet on screen].
- "caption" must be a ready-to-paste Instagram caption with 5-8 relevant hashtags at the end
- "hook" must be the opening spoken line — the scroll-stopper. Make it feel urgent or surprising.
- "virality_score" must be an integer from 0 to 100
"""


# ─── Pillar 2: Workflow Templates ─────────────────────────────────────────────

def build_workflow_prompt(theme: str) -> str:
    return f"""Generate a Reel script for a developer workflow.

WORKFLOW THEME: "{theme}"

Requirements:
- Make it feel like a workflow a senior engineer actually uses
- Name specific open-source tools for every step — no generic advice
- The spoken script should guide the viewer step-by-step
- Include visual cues [in brackets] showing what to put on screen (e.g. terminal commands, UI screenshots)

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping spoken opening line",
  "reel_script": "the full spoken script including visual cues in brackets",
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""


# ─── Pillar 3: Developer Roadmaps ─────────────────────────────────────────────

def build_roadmap_prompt(theme: str) -> str:
    return f"""Generate a Reel script for a developer learning roadmap.

ROADMAP THEME: "{theme}"

Requirements:
- Break the roadmap down into clear phases (Beginner, Intermediate, Advanced)
- Name specific free resources to learn from
- Tell them exactly what to BUILD at each stage — not just what to read
- End with a concrete "Start today" action
- Include visual cues [in brackets] showing roadmap graphics or code

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping spoken opening line",
  "reel_script": "the full spoken script including visual cues in brackets",
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""


# ─── Pillar 4: X vs Y Comparisons ────────────────────────────────────────────

def build_comparison_prompt(tool_a: str, tool_b: str) -> str:
    return f"""Generate a Reel script comparing two popular developer tools.

COMPARISON: {tool_a} vs {tool_b}

Requirements:
- Don't sit on the fence. Give a highly opinionated, honest verdict.
- Briefly mention the biggest strengths of {tool_a}.
- Briefly mention the biggest strengths of {tool_b}.
- Give a clear decision matrix ("Use {tool_a} if... Use {tool_b} if...")
- Include visual cues [in brackets] showing logos, code comparisons, or bullet points

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping spoken opening line creating tension between the tools",
  "reel_script": "the full spoken script including visual cues in brackets",
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""


# ─── Pillar 5: Problem → Solution Maps ───────────────────────────────────────

def build_problem_solution_prompt(theme: str) -> str:
    return f"""Generate a Reel script mapping a developer problem to an open-source solution stack.

THEME: "{theme}"

Requirements:
- Start by making the problem feel real and relatable (use "you" voice)
- Present the solution stack for a solo dev (simple, cheap)
- Present the solution stack for a team/startup (scaleable)
- Name specific open-source tools and repos
- Include visual cues [in brackets] showing architecture diagrams or tool logos

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping spoken opening line — make the problem urgent",
  "reel_script": "the full spoken script including visual cues in brackets",
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""


# ─── Pillar 7: Hidden Problem Posts ──────────────────────────────────────────

def build_hidden_problem_prompt(language: str, topic: str) -> str:
    return f"""Generate an educational Reel script revealing a hidden bug or silent mistake.

LANGUAGE/CONTEXT: {language}
PROBLEM: {topic}

Requirements:
- Make this feel like an urgent threat to the viewer's codebase
- Explain WHY the problem happens (the root cause)
- The script must instruct the viewer to look at the screen for the "BAD CODE" and the "FIXED CODE"
- Include precise visual cues [in brackets] showing EXACTLY what code should appear on screen
- Provide a clear way to grep or search their codebase to find the issue

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping scary opening line about their code",
  "reel_script": "the full spoken script including visual cues in brackets",
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""


# ─── Pillar 6: Weekly Trend Report ───────────────────────────────────────────

def build_trend_report_prompt(weekly_data: list[dict]) -> str:
    # Format the real data into a readable summary for the LLM
    top_repos = weekly_data[:10]  # top 10 by velocity
    repo_lines = []
    for r in top_repos:
        topics = ", ".join((r.get("topics") or [])[:3]) or "no topics"
        repo_lines.append(
            f"  - {r.get('full_name')} | ⭐ {r.get('stars_current', 0):,} "
            f"| velocity: {r.get('velocity_score', 0):.1f} | lang: {r.get('language', '?')} | topics: {topics}"
        )

    # Count languages
    lang_counts: dict[str, int] = {}
    for r in weekly_data:
        lang = r.get("language") or "Unknown"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    top_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    lang_str = ", ".join(f"{l} ({c})" for l, c in top_langs)

    data_block = "\n".join(repo_lines) if repo_lines else "  No repos discovered this week."

    return f"""Generate a Reel script for a weekly open-source trend report.

REAL DATA FROM THIS WEEK (use these actual numbers — do not hallucinate):
Total repos discovered: {len(weekly_data)}
Top repos by velocity score:
{data_block}
Top languages this week: {lang_str}

Requirements:
- Use the REAL numbers provided above. Quote actual velocity scores and star counts.
- Mention the top 1 or 2 repos that blew up and why they matter.
- Mention a language or category trend based on the counts above.
- What is the signal? (What does this mean for developers?)
- Include visual cues [in brackets] showing data charts or repo screenshots on screen

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping data-backed opening line",
  "reel_script": "the full spoken script including visual cues in brackets",
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""
