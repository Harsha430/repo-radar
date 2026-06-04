"""
config/settings.py — All configuration, thresholds, and environment loading for RepoRadar.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys ────────────────────────────────────────────────────────────────

GH_PAT: str = os.environ["GH_PAT"]
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# Support comma-separated list of Groq keys for round-robin rate limit bypassing
raw_groq_keys = os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", ""))
GROQ_API_KEYS: list[str] = [k.strip() for k in raw_groq_keys.split(",") if k.strip()]
if not GROQ_API_KEYS:
    GROQ_API_KEYS = [""]

# OpenAI-compatible API (e.g. OpenAI, Nvidia NIM, GPTOSS)
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
REDDIT_CLIENT_ID: str = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET: str = os.environ["REDDIT_CLIENT_SECRET"]
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]
# Telegram is optional — pipeline continues without it if unset
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ─── LLM Providers ───────────────────────────────────────────────────────────
# Can be "anthropic", "groq", or "openai"
FILTER_PROVIDER: str = os.getenv("FILTER_PROVIDER", os.getenv("LLM_PROVIDER", "groq"))
CONTENT_PROVIDER: str = os.getenv("CONTENT_PROVIDER", os.getenv("LLM_PROVIDER", "openai"))

# ─── Model Names ─────────────────────────────────────────────────────────────
# Anthropic models (used when LLM_PROVIDER="anthropic")
_ANTHROPIC_FILTER_MODEL  = "claude-haiku-4-5"     # Fast + cheap for quality check
_ANTHROPIC_RESEARCH_MODEL = "claude-opus-4-5"     # Deep analysis
_ANTHROPIC_CONTENT_MODEL  = "claude-opus-4-5"     # Content generation

# Groq models (used when provider="groq")
# llama-3.3-70b-versatile ≈ Opus quality; llama-3.1-8b-instant ≈ Haiku speed
_GROQ_FILTER_MODEL   = "llama-3.1-8b-instant"     # Ultra-fast, cheap
_GROQ_RESEARCH_MODEL = "llama-3.3-70b-versatile"  # Best Groq model for reasoning
_GROQ_CONTENT_MODEL  = "llama-3.3-70b-versatile"  # Same for creative generation

# OpenAI models (used when provider="openai")
_OPENAI_FILTER_MODEL   = os.getenv("OPENAI_FILTER_MODEL", "openai/gpt-oss-120b")
_OPENAI_RESEARCH_MODEL = os.getenv("OPENAI_RESEARCH_MODEL", "openai/gpt-oss-120b")
_OPENAI_CONTENT_MODEL  = os.getenv("OPENAI_CONTENT_MODEL", "openai/gpt-oss-120b")

# Active models (auto-selected by provider)
if FILTER_PROVIDER == "groq":
    FILTER_MODEL = _GROQ_FILTER_MODEL
elif FILTER_PROVIDER == "openai":
    FILTER_MODEL = _OPENAI_FILTER_MODEL
else:
    FILTER_MODEL = _ANTHROPIC_FILTER_MODEL

# Research/Content model resolution
if CONTENT_PROVIDER == "groq":
    RESEARCH_MODEL = _GROQ_RESEARCH_MODEL
    CONTENT_MODEL  = _GROQ_CONTENT_MODEL
elif CONTENT_PROVIDER == "openai":
    RESEARCH_MODEL = _OPENAI_RESEARCH_MODEL
    CONTENT_MODEL  = _OPENAI_CONTENT_MODEL
else:
    RESEARCH_MODEL = _ANTHROPIC_RESEARCH_MODEL
    CONTENT_MODEL  = _ANTHROPIC_CONTENT_MODEL

# ─── Pipeline Thresholds ─────────────────────────────────────────────────────

VELOCITY_THRESHOLD: float = 3.0               # Minimum velocity_score to pass filter
STARS_MIN: int = 1200
STARS_MAX: int = 50_000
REPO_AGE_MIN_DAYS: int = 1
REPO_AGE_MAX_DAYS: int = 730
README_MIN_LENGTH: int = 200                  # Characters
TOP_K_AFTER_FILTER: int = 1                   # Max repos sent to research agent
TOP_K_CONTENT: int = 1                        # Max repos for content generation
STARGAZER_PAGE_SIZE: int = 100               # Items per page for velocity computation

# ─── GitHub Search Queries ───────────────────────────────────────────────────

GITHUB_SEARCH_QUERIES: list[str] = [
    "topic:ai-agents stars:>1200 pushed:>2024-01-01 sort:stars-desc",
    "topic:agents stars:>1200 pushed:>2024-01-01",
    "topic:ai-workflows stars:>1200 pushed:>2024-01-01",
    "topic:llm-pipelines stars:>1200 pushed:>2024-01-01",
    "topic:llm-agents stars:>1200 pushed:>2024-01-01",
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

# ─── Content Pillar Schedule (weekday → pillar name) ─────────────────────────

DAILY_PILLAR_SCHEDULE: dict[int, str] = {
    0: "problem_solution",  # Monday
    1: "hidden_problem",    # Tuesday
    2: "comparison",        # Wednesday
    3: "workflow",          # Thursday
    4: "hidden_problem",    # Friday
    5: "roadmap",           # Saturday
    6: "trend_report",      # Sunday
}

# ─── Rotating Topic Lists ─────────────────────────────────────────────────────

WORKFLOW_THEMES: list[str] = [
    "local AI development stack with zero cloud costs",
    "CI/CD pipeline setup in 2025 with GitHub Actions",
    "Python project setup from scratch: linting, testing, pre-commit",
    "full stack deployment workflow on a $5 VPS",
    "data pipeline for ML projects end-to-end",
    "zero-cost self-hosted developer stack",
    "building and deploying a RAG chatbot in one day",
    "the perfect Docker Compose local dev environment",
    "go from idea to deployed app in under 2 hours",
    "automated testing workflow: unit, integration, e2e",
    "API development workflow: design, build, document, ship",
    "LLM fine-tuning workflow on consumer hardware",
    "monorepo workflow with Turborepo or Nx",
    "observability stack: logs, metrics, traces from scratch",
    "database migration workflow with zero downtime",
    "securing a web app: auth, HTTPS, secrets, rate limits",
    "building a personal knowledge base with open-source tools",
    "scraping and processing data at scale: the complete pipeline",
    "building a CLI tool and publishing it to PyPI",
    "local LLM inference workflow with Ollama + Open WebUI",
]

ROADMAP_THEMES: list[str] = [
    "backend development 2025",
    "machine learning engineering",
    "DevOps and platform engineering",
    "system design for software engineers",
    "open source contribution — from first PR to maintainer",
    "frontend development 2025",
    "AI/LLM engineering",
    "data engineering and pipelines",
    "security engineering",
    "cloud-native development",
    "mobile development with React Native or Flutter",
    "go from junior to senior engineer in 18 months",
    "database engineering: SQL, NoSQL, and beyond",
    "Rust programming for systems engineers",
    "building and shipping SaaS products as a solo developer",
]

COMPARISON_TOPICS: list[tuple[str, str]] = [
    ("FastAPI", "Django"),
    ("Prisma", "Drizzle"),
    ("LangChain", "LlamaIndex"),
    ("Docker", "Podman"),
    ("PostgreSQL", "MongoDB"),
    ("Redis", "Valkey"),
    ("Next.js", "Remix"),
    ("Vite", "Webpack"),
    ("Bun", "Node.js"),
    ("Pydantic", "Marshmallow"),
    ("SQLAlchemy", "Tortoise ORM"),
    ("Grafana", "Datadog"),
    ("GitHub Actions", "GitLab CI"),
    ("Supabase", "Firebase"),
    ("Weaviate", "Pinecone"),
    ("Ollama", "LM Studio"),
    ("Traefik", "Nginx"),
    ("Terraform", "Pulumi"),
    ("Celery", "Dramatiq"),
    ("pytest", "unittest"),
    ("Poetry", "uv"),
    ("Kafka", "RabbitMQ"),
    ("Prometheus", "InfluxDB"),
    ("Astro", "Hugo"),
    ("Tauri", "Electron"),
    ("dbt", "SQLMesh"),
    ("Airflow", "Prefect"),
    ("MinIO", "AWS S3"),
    ("Keycloak", "Authentik"),
    ("Qdrant", "Chroma"),
]

PROBLEM_TOPICS: list[tuple[str, str]] = [
    ("Python", "GIL and fake async with asyncio"),
    ("Docker", "running containers as root by default"),
    ("SQL", "N+1 query problem destroying API performance"),
    ("Git", "force pushing on shared branches"),
    ("JavaScript", "memory leaks from event listeners"),
    ("Python", "mutable default arguments in functions"),
    ("Docker", "bloated image sizes from bad layer caching"),
    ("PostgreSQL", "missing indexes on foreign keys"),
    ("Python", "circular imports silently breaking modules"),
    ("JavaScript", "the this keyword binding confusion"),
    ("Git", "committing secrets and API keys"),
    ("Python", "not using virtual environments"),
    ("API design", "returning 200 OK on errors"),
    ("SQL", "using SELECT star in production queries"),
    ("Docker", "not setting resource limits"),
    ("Python", "time.sleep in async code blocking the event loop"),
    ("JavaScript", "prototype pollution vulnerabilities"),
    ("Database", "not using transactions for multi-step writes"),
    ("Python", "catching bare Exception swallowing all errors"),
    ("Git", "not writing atomic commits"),
    ("API design", "pagination done wrong — offset vs cursor"),
    ("Python", "global state in web applications"),
    ("SQL", "using string concatenation for queries — SQL injection"),
    ("Docker", "not using .dockerignore causing huge build contexts"),
    ("Python", "datetime timezone naive vs aware bugs"),
    ("JavaScript", "blocking the main thread with synchronous code"),
    ("Database", "not setting connection pool limits"),
    ("Git", "enormous binary files committed to history"),
    ("Python", "import side effects breaking test isolation"),
    ("API design", "not versioning your API from day one"),
]

PROBLEM_SOLUTION_THEMES: list[str] = [
    "building a RAG pipeline — the exact open-source stack",
    "adding auth to your app — 4 options ranked",
    "self-hosting your entire stack — the complete guide",
    "scraping data at scale in 2025 — what actually works",
    "building an internal tool fast — the zero-cost stack",
    "setting up observability — logs, metrics, traces for free",
    "building a real-time feature — WebSockets vs SSE vs polling",
    "storing and querying vectors — the complete options guide",
    "running LLMs locally — the exact hardware and software stack",
    "building a task queue system from scratch",
    "handling file uploads at scale — the open-source way",
    "building a multi-tenant SaaS — the architecture options",
    "deploying ML models to production — 4 approaches ranked",
    "building a search feature — from basic to semantic",
    "setting up a CI/CD pipeline for free",
    "sending emails from your app — SPF, DKIM, and deliverability",
    "managing secrets and environment variables properly",
    "building a CLI tool that developers actually want to use",
    "caching everything — Redis, in-memory, CDN, edge",
    "database backups and disaster recovery on a budget",
    "building a webhook system that doesn't lose events",
    "handling payments without Stripe — the open-source options",
    "building a chatbot with memory — the architecture",
    "A/B testing without third-party tools",
    "end-to-end encryption for your app — the practical guide",
]
