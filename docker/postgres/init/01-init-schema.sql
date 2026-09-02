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
    'monthly'
);

CREATE TYPE domain_verification_code AS ENUM (
    'verified',
    'record_not_found',
    'token_mismatch',
    'lookup_failed'
);

CREATE TYPE activity_badge AS ENUM (
    'IN PROGRESS',
    'CRITICAL',
    'INFO'
);

CREATE TYPE engagement_type AS ENUM (
    'black_box',
    'grey_box',
    'white_box'
);

CREATE TYPE engagement_status AS ENUM (
    'requested',
    'scoping',
    'scheduled',
    'in_progress',
    'review',
    'completed',
    'cancelled'
);

CREATE TYPE finding_review_status AS ENUM (
    'draft',
    'ready_for_review',
    'published',
    'needs_revision'
);

CREATE TYPE engagement_message_channel AS ENUM (
    'client_service_delivery',
    'service_delivery_pentester'
    );

CREATE TYPE assessment_type AS ENUM (
    'web_application',
    'mobile_application',
    'api',
    'network',
    'cloud',
    'other'
);

CREATE TYPE retest_status AS ENUM (
    'requested',
    'in_progress',
    'resolved',
    'still_vulnerable'
);

CREATE TABLE organisations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
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

    UNIQUE (auth_provider, auth_provider_id),

    CHECK(role IN ('client', 'pentester', 'service_delivery', 'admin'))
);

CREATE TABLE pentester_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    company VARCHAR(255),
    bio TEXT,
    years_experience INTEGER,
    specialisations assessment_type[] NOT NULL DEFAULT '{}',
    certifications TEXT[] NOT NULL DEFAULT '{}',
    timezone VARCHAR(64),
    location VARCHAR(255),
    availability_status VARCHAR(30) NOT NULL DEFAULT 'available',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (years_experience IS NULL OR years_experience >= 0),
    CHECK (availability_status IN ('available', 'engaged', 'unavailable'))
);

CREATE TABLE verified_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    status domain_verification_status NOT NULL DEFAULT 'pending',
    verification_method VARCHAR(50) NOT NULL DEFAULT 'dns_txt',
    verification_token TEXT NOT NULL,
    verified_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_checked_at TIMESTAMPTZ,
    last_verification_code domain_verification_code,

    UNIQUE (user_id, domain)
);

CREATE TABLE scan_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scan_type scan_type NOT NULL DEFAULT 'active_vulnerability',
    verified_domain_id UUID NOT NULL REFERENCES verified_domains(id) ON DELETE CASCADE,
    frequency scan_schedule_frequency NOT NULL,
    run_time TIME NOT NULL,
    day_of_week SMALLINT,
    day_of_month SMALLINT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    next_run_at TIMESTAMPTZ NOT NULL,
    last_run_at TIMESTAMPTZ,
    timezone VARCHAR(64) NOT NULL DEFAULT 'Africa/Johannesburg',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (day_of_week IS NULL OR day_of_week BETWEEN 0 AND 6),
    CHECK (day_of_month IS NULL OR day_of_month BETWEEN 1 AND 28),

    UNIQUE (verified_domain_id, scan_type)
);

CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    task_id VARCHAR(255),
    domain VARCHAR(255) NOT NULL,
    verified_domain_id UUID REFERENCES verified_domains(id) ON DELETE SET NULL,
    schedule_id UUID REFERENCES scan_schedules(id) ON DELETE SET NULL DEFAULT NULL,
    scheduled_for TIMESTAMPTZ DEFAULT NULL,
    scan_type scan_type NOT NULL DEFAULT 'passive_ctem', 
    email VARCHAR(255),
    status scan_status NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,

    CHECK (progress >= 0 AND progress <= 100),
    CONSTRAINT uq_scans_schedule_occurrence UNIQUE (schedule_id, scheduled_for)
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
    state VARCHAR(50) NOT NULL DEFAULT 'open',
    service_name VARCHAR(100),
    product VARCHAR(255),
    version VARCHAR (255),
    banner TEXT,
    tls_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (scan_id, host, port, protocol),

    CHECK (port >= 1 AND port <= 65535)
);

CREATE TABLE engagements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID REFERENCES organisations(id) ON DELETE CASCADE,
    requested_by UUID NOT NULL REFERENCES users(id),
    service_delivery_id UUID REFERENCES users(id),
    assigned_to UUID REFERENCES users(id),
    engagement_type engagement_type NOT NULL,
    assessment_type assessment_type NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium',
    status engagement_status NOT NULL DEFAULT 'requested',
    title VARCHAR(255) NOT NULL,
    scope TEXT NOT NULL,
    objective TEXT,
    constraints TEXT,
    primary_contact VARCHAR(255),
    estimated_quote NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    final_quote NUMERIC(12,2),
    estimated_duration_days INTEGER,
    requested_start_date DATE,
    requested_end_date DATE,
    scheduled_start_date DATE,
    scheduled_end_date DATE,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_note TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (
        requested_start_date IS NULL
        OR requested_end_date IS NULL
        OR requested_start_date <= requested_end_date
    ),

    CHECK (
        scheduled_start_date IS NULL
        OR scheduled_end_date IS NULL
        OR scheduled_start_date <= scheduled_end_date
    )
);

CREATE TABLE engagement_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engagement_id UUID NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    identifier VARCHAR(255) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    asset_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    verified_domain_id UUID REFERENCES verified_domains(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(engagement_id, identifier, asset_type)
);

CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id) ON DELETE SET NULL,
    engagement_id UUID REFERENCES engagements(id) ON DELETE CASCADE,
    source VARCHAR(100) NOT NULL,
    status finding_status NOT NULL DEFAULT 'open',
    cvss_score NUMERIC(3,1),
    cve_id VARCHAR(50),
    service_id UUID REFERENCES services(id) ON DELETE SET NULL,
    severity finding_severity NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    recommendation TEXT,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_note TEXT,
    review_status finding_review_status,
    engagement_asset_id UUID REFERENCES engagement_assets(id) ON DELETE SET NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),

    CHECK (cvss_score IS NULL or (cvss_score >= 0 AND cvss_score <= 10)),
    CHECK ((scan_id IS NOT NULL) OR (engagement_id IS NOT NULL))
);

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID UNIQUE REFERENCES scans(id) ON DELETE CASCADE,
    engagement_id UUID REFERENCES engagements(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    task_id VARCHAR(255),
    status report_status NOT NULL DEFAULT 'pending',
    pdf_path TEXT,
    generated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error_message TEXT,

    CHECK(
        (scan_id IS NOT NULL AND engagement_id IS NULL)
        OR (scan_id IS NULL AND engagement_id IS NOT NULL)
    ),
    UNIQUE (engagement_id, version)
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

CREATE TABLE activity_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engagement_id UUID NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description TEXT NOT NULL,
    badge activity_badge,
    subtext VARCHAR(255)
);

CREATE TABLE engagement_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engagement_id UUID NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    finding_id UUID REFERENCES findings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    recipient_id UUID NOT NULL REFERENCES users(id),
    channel engagement_message_channel NOT NULL,
    comment TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    engagement_id UUID REFERENCES engagements(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE evidence_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    uploaded_by UUID REFERENCES users(id),
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    mime_type VARCHAR(100),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE finding_retests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    status retest_status NOT NULL DEFAULT 'requested',
    notes TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

ALTER TABLE scans ADD COLUMN IF NOT EXISTS schedule_id UUID REFERENCES scan_schedules(id) ON DELETE SET NULL DEFAULT NULL;
ALTER TABLE scans ADD COLUMN scheduled_for TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE scans ADD CONSTRAINT uq_scans_schedule_occurrence UNIQUE (schedule_id, scheduled_for);

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
CREATE INDEX idx_scans_schedule_id ON scans(schedule_id);

CREATE INDEX idx_services_scan_id ON services(scan_id);
CREATE INDEX idx_services_asset_id ON services(asset_id);
CREATE INDEX idx_services_host_port ON services(host, port);

CREATE INDEX idx_scan_schedule_verified_domain_id ON scan_schedules(verified_domain_id);
CREATE INDEX idx_scan_schedules_next_run_at ON scan_schedules(next_run_at) WHERE is_active = TRUE;
CREATE INDEX idx_scan_schedules_user_id ON scan_schedules(user_id);
CREATE INDEX idx_scan_schedules_is_active ON scan_schedules(is_active);

CREATE INDEX idx_scan_differences_current_scan_id ON scan_differences(current_scan_id);
CREATE INDEX idx_scan_differences_previous_scan_id ON scan_differences(previous_scan_id);

CREATE INDEX idx_detected_tech_scan_id ON detected_technologies(scan_id);
CREATE INDEX idx_detected_tech_asset_id ON detected_technologies(asset_id);
CREATE INDEX idx_detected_tech_service_id ON detected_technologies(service_id);
CREATE INDEX idx_detected_tech_product_ver ON detected_technologies(product, version);

CREATE INDEX idx_activity_events_engagement_id ON activity_events(engagement_id);
CREATE INDEX idx_engagement_status ON engagements(status);
CREATE INDEX idx_engagement_requested_by ON engagements(requested_by);
CREATE INDEX idx_engagement_assigned_to ON engagements(assigned_to);
CREATE INDEX idx_engagement_assets_engagement_id ON engagement_assets(engagement_id);
CREATE INDEX idx_engagement_assets_asset_type ON engagement_assets(asset_type);

CREATE INDEX idx_findings_engagement ON findings(engagement_id);

CREATE INDEX idx_notification_user ON notifications(user_id);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);

CREATE INDEX idx_finding_retests_finding_id ON finding_retests(finding_id);

CREATE INDEX idx_finding_retest_status ON finding_retests(status);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
