CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE organisations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    primary_domain VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE SET NULL,
    auth_provider VARCHAR(50) NOT NULL,
    auth_provider_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'client',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (auth_provider, auth_provider_id)
);

CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    domain VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,

    CHECK (progress >= 0 AND progress <= 100),
    CHECK (status IN ('queued', 'running', 'completed', 'failed', 'partial'))
);

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE SET NULL,
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    identifier VARCHAR(255) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (scan_id, identifier, asset_type)
);

CREATE TABLE scan_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    source_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    raw_result JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    UNIQUE (scan_id, source_name),
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial', 'skipped'))
);

CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id) ON DELETE SET NULL,
    source VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    recommendation TEXT,
    evidence JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (severity IN ('info', 'low', 'medium', 'high', 'critical'))
);

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    pdf_path TEXT,
    generated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error_message TEXT,

    CHECK (status IN ('pending', 'generating', 'completed', 'failed'))
);

CREATE INDEX idx_users_org_id ON users(organisation_id);
CREATE INDEX idx_scans_org_id ON scans(organisation_id);

CREATE INDEX idx_scans_user_id ON scans(user_id);
CREATE INDEX idx_scans_domain ON scans(domain);
CREATE INDEX idx_scans_status ON scans(status);

CREATE INDEX idx_assets_scan_id ON assets(scan_id);
CREATE INDEX idx_assets_org_id ON assets(organisation_id);

CREATE INDEX idx_sources_scan_id ON scan_sources(scan_id);

CREATE INDEX idx_findings_scan_id ON findings(scan_id);
CREATE INDEX idx_findings_asset_id ON findings(asset_id);
CREATE INDEX idx_findings_severity ON findings(severity);

CREATE INDEX idx_reports_scan_id ON reports(scan_id);