"""
prompts/pillar_prompts.py — LLM prompt builders for the 6 content pillars.

Each builder returns (system_prompt, user_prompt) and expects the LLM to
respond with a JSON object:
  {
    "hook":          string,
    "slides":        [{slide_num, headline, body, visual_cue}, ...],
    "caption":       string,
    "virality_score": int 0-100
  }
"""

# ─── Shared system prompt ─────────────────────────────────────────────────────

PILLAR_SYSTEM_PROMPT = """You are a viral tech content creator for Instagram and LinkedIn targeting software engineers aged 20-35.

Your content is:
- Punchy, specific, and technically credible
- Jargon-free but never dumbed-down
- Immediately actionable — devs should be able to use what they learn TODAY
- Original — never generic advice, always concrete examples

CRITICAL OUTPUT RULES:
- Respond ONLY with valid JSON. No markdown fences, no prose, no extra text.
- "slides" must be an array of objects: {slide_num (int), headline (string, <12 words), body (string, 40-60 words), visual_cue (string, what to show on screen)}
- "caption" must be a ready-to-paste Instagram caption with 5-8 relevant hashtags at the end
- "hook" must be the opening line — the scroll-stopper. Make it feel urgent or surprising.
- "virality_score" must be an integer from 0 to 100
"""


# ─── Pillar 2: Workflow Templates ─────────────────────────────────────────────

def build_workflow_prompt(theme: str) -> str:
    return f"""Generate a complete developer workflow carousel post for Instagram.

WORKFLOW THEME: "{theme}"

Requirements:
- 7 slides total
- Slide 1: The complete workflow as an overview (name every tool in the stack)
- Slides 2-7: One step each — tool name, what it does, how to set it up (include a real command or snippet)
- Make it feel like a workflow a senior engineer actually uses
- Name specific open-source tools for every step — no generic advice
- body for each slide should include at least one concrete command or config snippet

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping opening line (shown on story or reel)",
  "slides": [
    {{"slide_num": 1, "headline": "...", "body": "...", "visual_cue": "..."}},
    ...7 slides total...
  ],
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""


# ─── Pillar 3: Developer Roadmaps ─────────────────────────────────────────────

def build_roadmap_prompt(theme: str) -> str:
    return f"""Generate a complete developer learning roadmap carousel for Instagram.

ROADMAP THEME: "{theme}"

Requirements:
- 7 slides total
- Slide 1: Full roadmap overview — phases, total time estimate, what you'll be able to build
- Slides 2-6: One phase each (Beginner/Intermediate/Advanced/Projects/Resources)
  - Each phase: specific skills to learn, specific free resources (named), realistic time in weeks
  - What to BUILD at each stage — not just what to read
- Slide 7: "Start today" — the very first concrete step, today, right now
- Be honest about timelines. Don't say "learn X in 1 week" unless it's true.

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping opening line",
  "slides": [
    {{"slide_num": 1, "headline": "...", "body": "...", "visual_cue": "..."}},
    ...7 slides total...
  ],
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""


# ─── Pillar 4: X vs Y Comparisons ────────────────────────────────────────────

def build_comparison_prompt(tool_a: str, tool_b: str) -> str:
    return f"""Generate a head-to-head tool comparison carousel for Instagram.

COMPARISON: {tool_a} vs {tool_b}

Requirements:
- 6 slides total
- Slide 1: "The honest answer" — a one-paragraph verdict without fence-sitting
- Slide 2: {tool_a} — what it is, its 3 biggest strengths, who it's for
- Slide 3: {tool_b} — what it is, its 3 biggest strengths, who it's for
- Slide 4: Head-to-head table — pick 5 dimensions (performance, DX, ecosystem, learning curve, production-readiness)
- Slide 5: Decision matrix — "Use {tool_a} if you need X. Use {tool_b} if you need Y." (3-4 bullet points each)
- Slide 6: Final verdict — concrete recommendation based on the most common use case in 2025
- Be specific, opinionated, and accurate. Avoid "it depends" as a final answer.

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping opening line that creates tension between the two tools",
  "slides": [
    {{"slide_num": 1, "headline": "...", "body": "...", "visual_cue": "..."}},
    ...6 slides total...
  ],
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""


# ─── Pillar 5: Problem → Solution Maps ───────────────────────────────────────

def build_problem_solution_prompt(theme: str) -> str:
    return f"""Generate a problem-to-solution map carousel for developers on Instagram.

THEME: "{theme}"

Requirements:
- 6 slides total
- Slide 1: The problem — make it feel real and relatable (use "you" voice)
- Slide 2: Solution overview — what options exist, what we'll cover
- Slide 3: Stack for solo devs / indie hackers (cost, simplicity priority)
- Slide 4: Stack for startups (scale + speed priority)
- Slide 5: Stack for enterprise / teams (reliability + compliance priority)
- Slide 6: "Which one are you?" — direct CTA
- Name specific open-source tools and repos for every scenario
- For each tool: why it's in the stack, how it fits with the others, a one-line install command

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping opening line — make the problem feel urgent",
  "slides": [
    {{"slide_num": 1, "headline": "...", "body": "...", "visual_cue": "..."}},
    ...6 slides total...
  ],
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""


# ─── Pillar 7: Hidden Problem Posts ──────────────────────────────────────────

def build_hidden_problem_prompt(language: str, topic: str) -> str:
    return f"""Generate a "hidden bug / silent mistake" educational carousel for Instagram.

LANGUAGE/CONTEXT: {language}
PROBLEM: {topic}

Requirements:
- 6 slides total
- Slide 1: The scary hook — make this feel like a threat to the reader's code
- Slide 2: What this problem is and WHY it happens (root cause, not surface symptom)
- Slide 3: Show the BAD code — a short, realistic example that contains this exact bug
  visual_cue: "show this exact code snippet on screen"
- Slide 4: Show the FIXED code — the corrected version with the key change highlighted
  visual_cue: "show this exact code snippet on screen"
- Slide 5: How to FIND this in your existing codebase — grep command, linter rule, or code review checklist
- Slide 6: The takeaway — one rule of thumb to remember forever
- Be technically precise. The bad code and fixed code examples must be real and runnable.

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping scary opening line — this is about THEIR code",
  "slides": [
    {{"slide_num": 1, "headline": "...", "body": "...", "visual_cue": "..."}},
    ...6 slides total...
  ],
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

    return f"""Generate a weekly open-source trend report carousel for Instagram.

REAL DATA FROM THIS WEEK (use these actual numbers — do not hallucinate):
Total repos discovered: {len(weekly_data)}
Top repos by velocity score:
{data_block}
Top languages this week: {lang_str}

Requirements:
- 5 slides total
- Slide 1: "What's moving in open source this week" — hook with the most surprising stat from the real data
- Slide 2: Top 3 repos that blew up — name them, give real velocity scores, explain WHY they grew
- Slide 3: Language/category trends — what's hot, what's cooling down, based on real counts above
- Slide 4: The signal — what these trends tell us about where developer tooling is going
- Slide 5: "Follow to catch next week's report" — CTA
- Use the REAL numbers provided. Quote actual velocity scores and star counts.
- The narrative must be grounded in the data above.

Return a JSON object with these exact keys:
{{
  "hook": "the scroll-stopping data-backed opening line",
  "slides": [
    {{"slide_num": 1, "headline": "...", "body": "...", "visual_cue": "..."}},
    ...5 slides total...
  ],
  "caption": "full instagram caption with hashtags",
  "virality_score": 0-100
}}"""
