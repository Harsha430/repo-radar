"""
prompts/research_prompt.py — LLM prompts for the research agent (Claude Opus).
"""

RESEARCH_SYSTEM_PROMPT = """You are an expert open-source software analyst with deep knowledge of developer tooling, AI/ML frameworks, infrastructure, and programming languages.

Your task is to analyze a GitHub repository and produce a structured research report.

CRITICAL RULES:
- Respond ONLY with valid JSON. No markdown, no prose, no code fences.
- All array fields must be arrays (even if empty: []).
- Be concise but specific — avoid generic descriptions.
- Set is_real_project to false ONLY if the repo is clearly: a toy/demo, a fork with no changes, completely abandoned, or has no real-world use case.
"""

RESEARCH_JSON_SCHEMA = {
    "problem_solved": "string — what specific problem does this project solve?",
    "why_built": "string — what motivated the author to build this?",
    "target_audience": "string — who is the ideal user? (e.g. 'backend engineers', 'data scientists', 'sysadmins')",
    "alternatives": "array of strings — existing tools/projects that do similar things",
    "why_interesting": "string — what makes this novel or better than alternatives?",
    "architecture_summary": "string — how is it built? key design decisions, patterns used",
    "tech_stack": "array of strings — languages, frameworks, databases, protocols used",
    "pros": "array of strings — genuine strengths (3–5 items)",
    "cons": "array of strings — genuine weaknesses or limitations (2–4 items)",
    "is_real_project": "boolean — false only if toy/demo/fork/abandoned/no use case",
    "rejection_reason": "null or string — if is_real_project is false, explain why",
}


def build_research_prompt(repo: dict, readme: str) -> str:
    """
    Build the user message for the research agent.

    repo: dict with keys full_name, description, language, stars_current, topics, repo_age_days
    readme: raw README text (will be truncated to 4000 chars)
    """
    readme_excerpt = (readme or "")[:4000]
    topics_str = ", ".join(repo.get("topics") or []) or "none"

    return f"""Analyze this GitHub repository and return a JSON report.

REPOSITORY INFORMATION:
- Name: {repo.get("full_name", "unknown")}
- Description: {repo.get("description", "No description provided")}
- Primary Language: {repo.get("language", "Unknown")}
- Stars: {repo.get("stars_current", 0):,}
- Topics: {topics_str}
- Age: {repo.get("repo_age_days", 0)} days old
- License: {repo.get("license", "None")}
- Owner: {repo.get("owner_login", "Unknown")}

README (first 4000 chars):
---
{readme_excerpt}
---

Return a JSON object with EXACTLY these keys:
{_format_schema(RESEARCH_JSON_SCHEMA)}
"""


def _format_schema(schema: dict) -> str:
    lines = []
    for key, description in schema.items():
        lines.append(f'  "{key}": {description}')
    return "{\n" + ",\n".join(lines) + "\n}"
