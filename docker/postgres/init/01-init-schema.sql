CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE scan_status AS ENUM (
    'queued',
    'running',
    'completed',
    'failed',
    'partial'
);

CREATE TYPE scan_source_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed',
    'partial',
    'skipped'
);

CREATE TYPE finding_severity AS ENUM (
    'info',
    'low',
    'medium',
    'high',
    'critical'
);

CREATE TYPE report_status AS ENUM (
    'pending',
    'generating',
    'completed',
    'failed'
);

CREATE TYPE domain_verification_status AS ENUM (
    'pending',
    'verified',
    'failed',
    'expired'
);

CREATE TYPE scan_type AS ENUM (
    'passive_ctem',
    'active_vulnerability'
);

CREATE TYPE finding_status AS ENUM (
    'open',
    'in_progress',
    'resolved',
    'accepted_risk',
    'false_positive'
);

CREATE TYPE scan_schedule_frequency AS ENUM (
    'daily',
    'weekly',
    'monthly',
    'yearly'
);

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

CREATE TABLE verified_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    domain VARCHAR(255) NOT NULL,
    status domain_verification_status NOT NULL DEFAULT 'pending',
    verification_method VARCHAR(50) NOT NULL DEFAULT 'dns_txt',
    verification_token TEXT NOT NULL,
    verified_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (organisation_id, domain)
);

CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    task_id VARCHAR(255),
    domain VARCHAR(255) NOT NULL,
    verified_domain_id UUID REFERENCES verified_domains(id) ON DELETE SET NULL,
    scan_type scan_type NOT NULL DEFAULT 'passive_ctem', 
    email VARCHAR(255),
    status scan_status NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,

    CHECK (progress >= 0 AND progress <= 100)
);

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE SET NULL,
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    identifier VARCHAR(255) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    asset_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (scan_id, identifier, asset_type)
);

CREATE TABLE scan_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    source_name VARCHAR(100) NOT NULL,
    status scan_source_status NOT NULL DEFAULT 'pending',
    raw_result JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    UNIQUE (scan_id, source_name)
);

CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id) ON DELETE CASCADE,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    protocol VARCHAR(20) NOT NULL,
    service_name VARCHAR(100),
    product VARCHAR(255),
    version VARCHAR (255),
    banner TEXT,
    tls_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (scan_id, host, port, protocol),

    CHECK (port >= 1 AND port <= 65535)
);

CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id) ON DELETE SET NULL,
    source VARCHAR(100) NOT NULL,
    status finding_status NOT NULL DEFAULT 'open',
    cvss_score NUMERIC(3,1),
    cve_id VARCHAR(50),
    service_id UUID REFERENCES services(id) ON DELETE SET NULL,
    severity finding_severity NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    recommendation TEXT,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (cvss_score IS NULL or (cvss_score >= 0 AND cvss_score <= 10))
);

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL UNIQUE REFERENCES scans(id) ON DELETE CASCADE,
    task_id VARCHAR(255),
    status report_status NOT NULL DEFAULT 'pending',
    pdf_path TEXT,
    generated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error_message TEXT
);

CREATE TABLE scan_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_domain_id UUID NOT NULL REFERENCES verified_domains(id) ON DELETE CASCADE,
    frequency scan_schedule_frequency NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    next_run_at TIMESTAMPTZ NOT NULL,
    last_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE scan_differences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    current_scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    previous_scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
    new_findings_count INTEGER NOT NULL DEFAULT 0,
    unchanged_findings_count INTEGER NOT NULL DEFAULT 0,
    resolved_findings_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE detected_technologies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id) ON DELETE SET NULL,
    service_id UUID REFERENCES services(id) ON DELETE SET NULL,
    technology_type VARCHAR(50) NOT NULL,
    product VARCHAR(255) NOT NULL,
    version VARCHAR(255),
    confidence NUMERIC(4,3),
    detection_source VARCHAR(100),
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE NULLS NOT DISTINCT (scan_id, product, version, technology_type, asset_id, service_id),

    CHECK (confidence is NULL OR (confidence >= 0 AND confidence <= 1))
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
CREATE INDEX idx_findings_status ON findings(status);
CREATE INDEX idx_findings_cve_id ON findings(cve_id);
CREATE INDEX idx_findings_service_id ON findings(service_id);

CREATE INDEX idx_verified_domains_org_id ON verified_domains(organisation_id);
CREATE INDEX idx_verified_domains_domain ON verified_domains(domain);
CREATE INDEX idx_verified_domains_status ON verified_domains(status);

CREATE INDEX idx_scans_type ON scans(scan_type);
CREATE INDEX idx_scans_verified_domain_id ON scans(verified_domain_id);

CREATE INDEX idx_services_scan_id ON services(scan_id);
CREATE INDEX idx_services_asset_id ON services(asset_id);
CREATE INDEX idx_services_host_port ON services(host, port);

CREATE INDEX idx_scan_schedule_verified_domain_id ON scan_schedules(verified_domain_id);
CREATE INDEX idx_scan_schedules_next_run_at ON scan_schedules(next_run_at);
CREATE INDEX idx_scan_schedules_is_active ON scan_schedules(is_active);

CREATE INDEX idx_scan_differences_current_scan_id ON scan_differences(current_scan_id);
CREATE INDEX idx_scan_differences_previous_scan_id ON scan_differences(previous_scan_id);

CREATE INDEX idx_detected_tech_scan_id ON detected_technologies(scan_id);
CREATE INDEX idx_detected_tech_asset_id ON detected_technologies(asset_id);
CREATE INDEX idx_detected_tech_service_id ON detected_technologies(service_id);
CREATE INDEX idx_detected_tech_product_ver ON detected_technologies(product, version);