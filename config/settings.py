"""
config/settings.py — All configuration, thresholds, and environment loading for RepoRadar.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys ────────────────────────────────────────────────────────────────

GH_PAT: str = os.environ["GH_PAT"]
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
REDDIT_CLIENT_ID: str = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET: str = os.environ["REDDIT_CLIENT_SECRET"]
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]
# Telegram is optional — pipeline continues without it if unset
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ─── LLM Provider ────────────────────────────────────────────────────────────
# Set to "anthropic" or "groq"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")

# ─── Model Names ─────────────────────────────────────────────────────────────
# Anthropic models (used when LLM_PROVIDER="anthropic")
_ANTHROPIC_FILTER_MODEL  = "claude-haiku-4-5"     # Fast + cheap for quality check
_ANTHROPIC_RESEARCH_MODEL = "claude-opus-4-5"     # Deep analysis
_ANTHROPIC_CONTENT_MODEL  = "claude-opus-4-5"     # Content generation

# Groq models (used when LLM_PROVIDER="groq")
# llama-3.3-70b-versatile ≈ Opus quality; llama-3.1-8b-instant ≈ Haiku speed
_GROQ_FILTER_MODEL   = "llama-3.1-8b-instant"     # Ultra-fast, cheap
_GROQ_RESEARCH_MODEL = "llama-3.3-70b-versatile"  # Best Groq model for reasoning
_GROQ_CONTENT_MODEL  = "llama-3.3-70b-versatile"  # Same for creative generation

# Active models (auto-selected by provider)
if LLM_PROVIDER == "groq":
    FILTER_MODEL   = _GROQ_FILTER_MODEL
    RESEARCH_MODEL = _GROQ_RESEARCH_MODEL
    CONTENT_MODEL  = _GROQ_CONTENT_MODEL
else:
    FILTER_MODEL   = _ANTHROPIC_FILTER_MODEL
    RESEARCH_MODEL = _ANTHROPIC_RESEARCH_MODEL
    CONTENT_MODEL  = _ANTHROPIC_CONTENT_MODEL

# ─── Pipeline Thresholds ─────────────────────────────────────────────────────

VELOCITY_THRESHOLD: float = 3.0               # Minimum velocity_score to pass filter
STARS_MIN: int = 20
STARS_MAX: int = 50_000
REPO_AGE_MIN_DAYS: int = 1
REPO_AGE_MAX_DAYS: int = 730
README_MIN_LENGTH: int = 200                  # Characters
TOP_K_AFTER_FILTER: int = 1                   # Max repos sent to research agent
TOP_K_CONTENT: int = 1                        # Max repos for content generation
STARGAZER_PAGE_SIZE: int = 100               # Items per page for velocity computation

# ─── GitHub Search Queries ───────────────────────────────────────────────────

GITHUB_SEARCH_QUERIES: list[str] = [
    "stars:50..5000 pushed:>2024-01-01 sort:stars-desc",
    "topic:ai stars:20..3000 pushed:>2024-01-01",
    "topic:llm stars:20..3000 pushed:>2024-01-01",
    "topic:rust stars:20..5000 pushed:>2024-06-01",
    "topic:developer-tools stars:20..5000 pushed:>2024-01-01",
    "topic:self-hosted stars:20..3000 pushed:>2024-01-01",
    "topic:open-source stars:20..2000 pushed:>2025-01-01",
]

# ─── Reddit Subreddits ───────────────────────────────────────────────────────

REDDIT_SUBREDDITS: list[str] = [
    "programming",
    "opensource",
    "LocalLLaMA",
    "selfhosted",
    "devops",
    "Python",
    "webdev",
]
REDDIT_POST_LIMIT: int = 25                   # Posts to scan per subreddit
REDDIT_USER_AGENT: str = "RepoRadar/1.0 (github.com/reporadar)"

# ─── Hacker News ─────────────────────────────────────────────────────────────

HN_LOOKBACK_HOURS: int = 36

# ─── GitHub Rate Limit ───────────────────────────────────────────────────────

GITHUB_RATE_LIMIT_RETRIES: int = 3

# ─── Content Scoring Weights ─────────────────────────────────────────────────

SCORE_WEIGHT_VIRALITY: float = 0.4
SCORE_WEIGHT_LEARNING: float = 0.3
SCORE_WEIGHT_INNOVATION: float = 0.3
