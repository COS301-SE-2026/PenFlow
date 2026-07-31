-- NOSONAR

INSERT INTO organisations (id, name)
VALUES
('11111111-1111-1111-1111-111111111111', 'Acme Security Ltd')
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, organisation_id, auth_provider, auth_provider_id, email, full_name, role)
VALUES
(
  '22222222-2222-2222-2222-222222222222',
  '11111111-1111-1111-1111-111111111111',
  'keycloak',
  '6f9d91d4-8c3a-4c8e-9b12-demo-user',
  'security.lead@acme-security.example',
  'Jordan Taylor',
  'client'
)
ON CONFLICT (auth_provider, auth_provider_id) DO NOTHING;

INSERT INTO scans (id, organisation_id, user_id, domain, email, status, progress, completed_at)
VALUES
(
  '33333333-3333-3333-3333-333333333333',
  '11111111-1111-1111-1111-111111111111',
  '22222222-2222-2222-2222-222222222222',
  'acme-security.example',
  NULL,
  'completed',
  100,
  NOW()
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO scan_sources (scan_id, source_name, status, raw_result, completed_at)
VALUES
(
  '33333333-3333-3333-3333-333333333333',
  'crt_sh',
  'completed',
  '{"subdomains":{"provider":"crt.sh","total_found":6,"discovered_names":["acme-security.example","www.acme-security.example","app.acme-security.example","api.acme-security.example","mail.acme-security.example","vpn.acme-security.example"]}}'::jsonb,
  NOW()
),
(
  '33333333-3333-3333-3333-333333333333',
  'urlscan',
  'completed',
  '{"reputation":{"provider":"URLScan","malicious_flags":0,"urlscan_uuid":"019e-demo-scan-uuid","screenshot_url":"default.png","screenshot_path":"default.png"}}'::jsonb,
  NOW()
),
(
  '33333333-3333-3333-3333-333333333333',
  'dns',
  'completed',
  '{"domain_security":{"provider":"DNS/RDAP","records":[{"record_type":"MX","status":"Pass","finding":"MX records are configured for this domain."},{"record_type":"SPF","status":"Pass","finding":"SPF record is present and uses a hard fail policy."},{"record_type":"DMARC","status":"Warning","finding":"DMARC record is present but policy is set to monitoring only."},{"record_type":"WHOIS/RDAP","status":"Pass","finding":"WHOIS/RDAP registration data was available for this domain."}],"detected_services":["Google Workspace","Slack","Atlassian","Microsoft 365","Cloudflare"],"whois":{"provider":"RDAP","registrar":"Cloudflare, Inc.","registration_date":"2021-03-14T10:22:00Z","expiration_date":"2027-03-14T10:22:00Z","dnssec_enabled":true,"nameservers":["NS1.CLOUDFLARE.COM","NS2.CLOUDFLARE.COM"]}}}'::jsonb,
  NOW()
),
(
  '33333333-3333-3333-3333-333333333333',
  'wappalyzer',
  'completed',
  '{"tech_stack":{"provider":"Wappalyzer","cms":[],"frameworks":[{"name":"React","version":"Unknown"},{"name":"jQuery","version":"3.6.0"}],"webServers":[{"name":"Nginx","version":"Unknown"}],"paas":[],"programmingLanguages":[{"name":"PHP","version":"8.1"}],"databases":[],"cdn":[{"name":"Cloudflare","version":"Unknown"}]}}'::jsonb,
  NOW()
),
(
  '33333333-3333-3333-3333-333333333333',
  'shodan',
  'completed',
  '{"infrastructure":{"hosting_provider":"Cloudflare, Inc.","ip_addresses":["104.21.32.10","172.67.181.45"],"open_ports":[{"port":80,"state":"open"},{"port":443,"state":"open"}]}}'::jsonb,
  NOW()
),
(
  '33333333-3333-3333-3333-333333333333',
  'hunter.io',
  'completed',
  '{"phishing_surface":{"provider":"Hunter.io","email_format_pattern":"{first}.{last}","public_emails_found":[{"email":"security@acme-security.example","type":"generic","confidence_score":91},{"email":"it.support@acme-security.example","type":"generic","confidence_score":84}]}}'::jsonb,
  NOW()
),
(
  '33333333-3333-3333-3333-333333333333',
  'hibp',
  'completed',
  '{"breach_data":{"provider":"HaveIBeenPwned","pwned_accounts_count":2,"known_breaches":["LinkedIn","Collection1"]}}'::jsonb,
  NOW()
)
ON CONFLICT (scan_id, source_name) DO NOTHING;

INSERT INTO assets (scan_id, identifier, asset_type)
VALUES
('33333333-3333-3333-3333-333333333333', 'www.acme-security.example', 'subdomain'),
('33333333-3333-3333-3333-333333333333', 'app.acme-security.example', 'subdomain'),
('33333333-3333-3333-3333-333333333333', 'api.acme-security.example', 'subdomain'),
('33333333-3333-3333-3333-333333333333', 'mail.acme-security.example', 'subdomain'),
('33333333-3333-3333-3333-333333333333', 'vpn.acme-security.example', 'subdomain'),
('33333333-3333-3333-3333-333333333333', '104.21.32.10', 'ip_address'),
('33333333-3333-3333-3333-333333333333', '172.67.181.45', 'ip_address'),
('33333333-3333-3333-3333-333333333333', 'security@acme-security.example', 'email'),
('33333333-3333-3333-3333-333333333333', 'it.support@acme-security.example', 'email')
ON CONFLICT (scan_id, identifier, asset_type) DO NOTHING;

INSERT INTO findings (scan_id, source, severity, title, description, recommendation, evidence)
VALUES
(
  '33333333-3333-3333-3333-333333333333',
  'dns',
  'medium',
  'DMARC Policy Is Not Enforced',
  'The domain has a DMARC record, but it is configured in monitoring mode rather than enforcement mode.',
  'Update the DMARC policy to quarantine or reject once mail flow has been validated.',
  '{"record_type":"DMARC","policy":"p=none"}'::jsonb
),
(
  '33333333-3333-3333-3333-333333333333',
  'hunter.io',
  'info',
  'Public Email Addresses Discovered',
  'Publicly accessible email addresses were discovered for this domain.',
  'Ensure exposed mailboxes are protected with MFA and phishing-resistant security controls.',
  '{"emails":["security@acme-security.example","it.support@acme-security.example"]}'::jsonb
),
(
  '33333333-3333-3333-3333-333333333333',
  'hibp',
  'high',
  'Historical Breach Exposure Detected',
  'Accounts associated with the domain were found in historical third-party breach datasets.',
  'Enforce MFA, review password reuse risk, and require password resets for affected accounts.',
  '{"pwned_accounts_count":2,"known_breaches":["LinkedIn","Collection1"]}'::jsonb
),
(
  '33333333-3333-3333-3333-333333333333',
  'wappalyzer',
  'info',
  'Commonly Targeted Technology Detected: PHP',
  'The target appears to use PHP, which requires regular patching and version lifecycle management.',
  'Ensure PHP is running a supported version and that dependency patching is monitored.',
  '{"technology":"PHP","version":"8.1"}'::jsonb
);

INSERT INTO reports (scan_id, status, pdf_path, generated_at)
VALUES
(
  '33333333-3333-3333-3333-333333333333',
  'completed',
  '/app/generated_reports/ctem_report_33333333-3333-3333-3333-333333333333.pdf',
  NOW()
)
ON CONFLICT (scan_id) DO NOTHING;