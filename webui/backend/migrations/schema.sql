-- SimpleSecCheck PostgreSQL Schema
-- This schema is automatically created by the PostgreSQLDatabase adapter
-- But can be used for manual setup or migrations

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    scans_requested INTEGER DEFAULT 0,
    rate_limit_scans INTEGER DEFAULT 10,
    rate_limit_requests INTEGER DEFAULT 100,
    ip_address TEXT
);

-- Queue table
CREATE TABLE IF NOT EXISTS queue (
    queue_id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    repository_url TEXT NOT NULL,
    repository_name TEXT NOT NULL,
    branch TEXT,
    commit_hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    position INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    scan_id TEXT,
    CONSTRAINT status_check CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

-- Indexes for queue
CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status);
CREATE INDEX IF NOT EXISTS idx_queue_session ON queue(session_id);
CREATE INDEX IF NOT EXISTS idx_queue_created ON queue(created_at);

-- Metadata table
CREATE TABLE IF NOT EXISTS scan_metadata (
    id SERIAL PRIMARY KEY,
    repository_url TEXT NOT NULL,
    branch TEXT NOT NULL,
    commit_hash TEXT NOT NULL,
    scan_id TEXT NOT NULL,
    scan_date TIMESTAMP NOT NULL DEFAULT NOW(),
    findings_count INTEGER DEFAULT 0,
    metadata_file_path TEXT,
    UNIQUE(repository_url, branch, commit_hash)
);

-- Indexes for metadata
CREATE INDEX IF NOT EXISTS idx_metadata_repo ON scan_metadata(repository_url, branch, commit_hash);
CREATE INDEX IF NOT EXISTS idx_metadata_date ON scan_metadata(scan_date);

-- Statistics table
CREATE TABLE IF NOT EXISTS statistics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_scans INTEGER DEFAULT 0,
    total_findings INTEGER DEFAULT 0,
    findings_by_severity JSONB DEFAULT '{}',
    findings_by_tool JSONB DEFAULT '{}',
    false_positive_count INTEGER DEFAULT 0,
    UNIQUE(date)
);
