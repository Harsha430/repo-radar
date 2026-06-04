-- ═══════════════════════════════════════════════════════════════════════════
-- RepoRadar — Supabase Schema
-- Run this once in the Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- ═══════════════════════════════════════════════════════════════════════════

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: repos
-- Every repository ever discovered. Primary deduplication guard.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS repos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id           BIGINT UNIQUE NOT NULL,
    full_name           TEXT NOT NULL,
    url                 TEXT NOT NULL,
    description         TEXT,
    language            TEXT,
    topics              TEXT[],
    license             TEXT,
    stars_at_discovery  INT,
    stars_current       INT,
    forks               INT,
    velocity_score      FLOAT,
    stars_gained_24h    INT,
    source              TEXT CHECK (source IN ('github_trending', 'github_search', 'hn', 'reddit')),
    source_metadata     JSONB,
    passed_filter       BOOLEAN,              -- NULL = not yet evaluated
    filter_reason       TEXT,                 -- Reason for rejection (if any)
    owner_login         TEXT,
    repo_age_days       INT,
    first_seen_at       TIMESTAMPTZ DEFAULT NOW(),
    last_checked_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_repos_github_id ON repos (github_id);
CREATE INDEX IF NOT EXISTS idx_repos_passed_filter ON repos (passed_filter);
CREATE INDEX IF NOT EXISTS idx_repos_first_seen_at ON repos (first_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_repos_velocity_score ON repos (velocity_score DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: research
-- Deep AI analysis for each candidate repo.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS research (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id              UUID NOT NULL REFERENCES repos (id) ON DELETE CASCADE,
    problem_solved       TEXT,
    why_built            TEXT,
    target_audience      TEXT,
    alternatives         TEXT[],
    why_interesting      TEXT,
    architecture_summary TEXT,
    tech_stack           TEXT[],
    pros                 TEXT[],
    cons                 TEXT[],
    raw_readme           TEXT,
    raw_llm_response     JSONB,
    researched_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_repo_id ON research (repo_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: content
-- Generated Instagram Reel content for selected repos.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS content (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id                 UUID NOT NULL REFERENCES repos (id) ON DELETE CASCADE,
    research_id             UUID REFERENCES research (id) ON DELETE SET NULL,
    reel_script             TEXT,
    creator_notes           TEXT,
    technical_breakdown     TEXT,
    virality_score          INT CHECK (virality_score BETWEEN 0 AND 100),
    learning_score          INT CHECK (learning_score BETWEEN 0 AND 100),
    innovation_score        INT CHECK (innovation_score BETWEEN 0 AND 100),
    overall_score           FLOAT,           -- 40% virality + 30% learning + 30% innovation
    posted_to_instagram     BOOLEAN DEFAULT FALSE,
    generated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_repo_id ON content (repo_id);
CREATE INDEX IF NOT EXISTS idx_content_overall_score ON content (overall_score DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: daily_runs
-- Audit log of every pipeline execution.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_date            DATE UNIQUE NOT NULL DEFAULT CURRENT_DATE,
    discovered_count    INT DEFAULT 0,
    after_filter_count  INT DEFAULT 0,
    researched_count    INT DEFAULT 0,
    content_generated   INT DEFAULT 0,
    selected_repo_ids   UUID[],
    whatsapp_sent       BOOLEAN DEFAULT FALSE,
    duration_seconds    INT,
    error_log           TEXT,
    status              TEXT DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed')),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_runs_run_date ON daily_runs (run_date DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Table: pillar_content
-- Generated content for the 6 rotating content pillars (workflows, roadmaps, etc.)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pillar_content (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pillar          TEXT NOT NULL CHECK (pillar IN (
                        'workflow', 'roadmap', 'comparison',
                        'problem_solution', 'hidden_problem', 'trend_report'
                    )),
    theme           TEXT NOT NULL,       -- The specific topic used (e.g. "FastAPI vs Django")
    hook            TEXT NOT NULL,       -- The opening hook line
    reel_script     TEXT NOT NULL,       -- Spoken script for the short-form video
    caption         TEXT NOT NULL,       -- Ready-to-post Instagram caption
    virality_score  INT CHECK (virality_score BETWEEN 0 AND 100),
    generated_at    TIMESTAMPTZ DEFAULT NOW(),
    posted          BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_pillar_content_pillar ON pillar_content (pillar);
CREATE INDEX IF NOT EXISTS idx_pillar_content_generated_at ON pillar_content (generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_pillar_content_posted ON pillar_content (posted);
