-- ============================================================
-- LabAI — Supabase SQL Schema
-- Run this ONCE in: Supabase → SQL Editor → New Query → Run
-- ============================================================

-- 1. Training data uploaded by admin (approved OCR results)
CREATE TABLE IF NOT EXISTS training_data (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT DEFAULT 'admin',
    filename    TEXT,
    val_count   INTEGER DEFAULT 0,
    values_json JSONB  DEFAULT '{}',
    features    JSONB  DEFAULT '[]',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Anonymous user uploads (for admin view + training pool)
CREATE TABLE IF NOT EXISTS user_uploads (
    id          BIGSERIAL PRIMARY KEY,
    filename    TEXT,
    val_count   INTEGER DEFAULT 0,
    flagged_cnt INTEGER DEFAULT 0,
    ml_score    INTEGER,
    values_json JSONB  DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Trained TF.js model weights (single row, id always = 'current')
CREATE TABLE IF NOT EXISTS model_weights (
    id            TEXT PRIMARY KEY DEFAULT 'current',
    weights_json  JSONB   DEFAULT '[]',
    stats_json    JSONB   DEFAULT '{}',
    version       INTEGER DEFAULT 1,
    training_size INTEGER DEFAULT 0,
    trained_at    TIMESTAMPTZ
);

-- 4. Batch OCR jobs (one per bulk upload)
CREATE TABLE IF NOT EXISTS batch_jobs (
    id         BIGSERIAL PRIMARY KEY,
    total      INTEGER DEFAULT 0,
    processed  INTEGER DEFAULT 0,
    saved      INTEGER DEFAULT 0,
    skipped    INTEGER DEFAULT 0,
    failed     INTEGER DEFAULT 0,
    status     TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Individual images inside a batch job
CREATE TABLE IF NOT EXISTS batch_items (
    id          BIGSERIAL PRIMARY KEY,
    job_id      BIGINT REFERENCES batch_jobs(id) ON DELETE CASCADE,
    filename    TEXT,
    status      TEXT DEFAULT 'waiting',
    val_count   INTEGER DEFAULT 0,
    values_json JSONB DEFAULT '{}',
    error       TEXT DEFAULT ''
);

-- ── Indexes for performance ──────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_training_source   ON training_data(source);
CREATE INDEX IF NOT EXISTS idx_training_created  ON training_data(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_uploads_created   ON user_uploads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_batch_items_job   ON batch_items(job_id);
CREATE INDEX IF NOT EXISTS idx_batch_items_status ON batch_items(status);

-- ── Row Level Security ────────────────────────────────────────────
-- Enable RLS on all tables
ALTER TABLE training_data  ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_uploads   ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_weights  ENABLE ROW LEVEL SECURITY;
ALTER TABLE batch_jobs     ENABLE ROW LEVEL SECURITY;
ALTER TABLE batch_items    ENABLE ROW LEVEL SECURITY;

-- Anyone can READ model weights (needed for user-side ML scoring)
CREATE POLICY "public_read_model"
    ON model_weights FOR SELECT
    USING (true);

-- Anyone can INSERT user uploads (anonymous, no personal data)
CREATE POLICY "public_insert_uploads"
    ON user_uploads FOR INSERT
    WITH CHECK (true);

-- All other access requires service role key (used by Django backend)
-- Django uses the service key which bypasses RLS entirely.
-- No additional policies needed for admin operations.

-- ============================================================
-- DONE. Your 5 tables are ready.
-- Now copy your Supabase credentials into Django settings:
--   Project Settings → API → Project URL  → SUPABASE_URL
--   Project Settings → API → service_role  → DATABASE_URL
--   (use the direct connection string from Settings → Database)
-- ============================================================