# 📡 RepoRadar

**RepoRadar** is an autonomous Python agentic pipeline that discovers breakout open-source GitHub repositories *before* they go viral. 

It runs completely autonomously via GitHub Actions every day at 6:00 AM IST, aggregates data across 4 platforms, uses LLMs to conduct deep research, generates ready-to-post viral content for social media (e.g., Instagram Reels), and delivers the final report directly to your Telegram.

---

## 🚀 How it Works

The pipeline is orchestrated as a state machine using **LangGraph** with 4 distinct agentic nodes:

1. **Discovery Agent**: Scrapes and queries 4 sources in parallel (GitHub Trending, GitHub Search API, Hacker News, and 7 programming subreddits) to find new repositories. *Currently strictly configured to hunt for AI Agents, AI Workflows, and LLM Pipelines with over 1,200 stars.*
2. **Filter Agent**: Calculates a "Velocity Score" (stars per hour) to surface unusually fast-growing repos, and uses an ultra-fast LLM (e.g., Groq Llama 3) as a quality gate to drop spam or low-effort projects. *Utilizes a round-robin API key rotator and a 3.5-second pacing lock to completely bypass free-tier rate limits.*
3. **Research Agent**: Fetches the READMEs and repository metadata of the filtered repos, then runs deep parallel analysis to understand the problem solved, tech stack, architecture, pros, and cons.
4. **Generator Agent**: Scores the researched repos based on a novelty heuristic, selects the top tier, and generates 60-90 second viral "Deep Dive" reel scripts and technical breakdowns. Finally, a Telegram client formats (using safe HTML parsing) and sends the daily summary to your phone.

Everything is stored persistently in a **Supabase (PostgreSQL)** database (with a 2-second write pacing to prevent connection drops) to ensure repos are never processed twice and to track historical velocity data.

---

## 🛠️ Tech Stack

- **Core**: Python 3.10+, LangGraph (Orchestration)
- **Data Sources**: GitHub REST API, BeautifulSoup4 (Scraping), PRAW (Reddit API), Hacker News Firebase API
- **AI/LLMs**: Unified multi-provider client supporting **Groq** (with round-robin key rotation), **Anthropic**, and **OpenAI-compatible endpoints** (like Nvidia NIM / GPT-OSS). Separate providers can be configured for Filtering vs. Content Generation.
- **Database**: Supabase (PostgreSQL)
- **Notifications**: Telegram Bot
- **Automation**: GitHub Actions

---

## ⚙️ Setup & Installation

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/repo_radar.git
cd repo_radar
pip install -r requirements.txt
```

### 2. Database Setup
1. Create a free project on [Supabase](https://supabase.com).
2. Go to the **SQL Editor** in the Supabase dashboard.
3. Copy the contents of `db/schema.sql` and run it to create the required tables and indexes.

### 3. Environment Variables
Copy the example environment file and fill in your keys:
```bash
cp .env.example .env
```
You will need to configure these credentials in your `.env`:
- `GH_PAT`: GitHub Fine-Grained Personal Access Token (Read-Only)
- `FILTER_PROVIDER`: Set to `groq`, `anthropic`, or `openai` (used for the fast quality gate)
- `CONTENT_PROVIDER`: Set to `openai`, `groq`, or `anthropic` (used for heavy generation)
- `GROQ_API_KEYS`: Comma-separated list of Groq keys (e.g. `gsk_1,gsk_2`) to enable automatic rate-limit bypassing
- `OPENAI_API_KEY` & `OPENAI_BASE_URL`: For custom models like Nvidia NIM (`gpt-oss-120b`)
- `ANTHROPIC_API_KEY`: If using Claude models
- `REDDIT_CLIENT_ID` & `REDDIT_CLIENT_SECRET`: From a Reddit "script" app
- `SUPABASE_URL` & `SUPABASE_KEY`
- `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: From Telegram BotFather

*(See the inline comments in `.env.example` for where to obtain each key).*

---

## 💻 Running the Pipeline

### Locally
Run the orchestrator script directly:
```bash
python main.py
```
You will see rich terminal logging detailing the progress of each agent.

### Autonomously (GitHub Actions)
The repository includes a `.github/workflows/daily_run.yml` file configured to run the pipeline automatically via cron job.
To enable it:
1. Go to your GitHub repository **Settings → Secrets and variables → Actions**.
2. Add all the keys from your `.env` file as Repository Secrets.
3. The pipeline will now run unattended every day.

---

## 📂 Architecture overview

```text
repo_radar/
├── agents/             # LangGraph Nodes
│   ├── discovery_agent.py
│   ├── filter_agent.py
│   ├── research_agent.py
│   └── generator_agent.py
├── config/
│   └── settings.py     # Centralized thresholds and model config
├── core/               # API Clients
│   ├── github_client.py
│   ├── reddit_client.py
│   ├── hn_client.py
│   ├── llm_client.py   # Unified Groq/Anthropic interface
│   └── whatsapp_client.py
├── db/
│   ├── schema.sql
│   └── supabase_client.py
├── prompts/            # System instructions for LLMs
├── main.py             # LangGraph workflow compiler & runner
└── requirements.txt
```

## 📜 License
MIT License
